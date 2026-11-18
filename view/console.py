# ruff: noqa: RUF001
import os
import signal
import sys
from datetime import UTC
from pathlib import Path
from queue import Empty, Queue
from threading import Event, Thread, current_thread, main_thread
from typing import TextIO

from area_attacks import CircleAttack, StraightAttack, WaveAttack
from bonuses import IDCard, OneTimeBonus
from game import ActorParams
from generation import (
    BossLevelGenerator,
    CommonLevelGenerator,
    MonsterAttackGenerator,
    MonsterParamsGenerator,
    MonsterStrategyGenerator,
)
from hero import Hero, IEvent, OneTimeBonusEvent
from monster_strategies.simple_monster_strategy import SimpleMonsterStrategy
from play_cycle import GlobalConfig, IModelSubscriber
from play_cycle.game import Game
from positioning import Direction, ICellObject, Position
from serializing import GameLoader
from view.renderer import render, supports_ansi


class _QuitAtBoundary(Exception):
    pass


class _PassEvent(IEvent):
    def accept_hero(self, hero: Hero) -> None:
        """Finish one action without changing the hero."""


class _MoveEvent(IEvent):
    def __init__(self, direction: Direction, console: "Console") -> None:
        self._direction = direction
        self._console = console

    def accept_hero(self, hero: Hero) -> None:
        """Execute movement and report when it fails."""
        succeeded = hero.try_move(self._direction)
        hero.set_action_succeeded(succeeded)
        if not succeeded:
            self._console._actions_used -= 1
            self._console.message("Движение невозможно.")


class _SpecialEvent(IEvent):
    def __init__(self, console: "Console") -> None:
        self._console = console

    def accept_hero(self, hero: Hero) -> None:
        """Execute the special attack and report unavailable attacks."""
        card = hero.get_current_id_card()
        if card is None:
            self._console.message("Удостоверение не выбрано.")
            self._console._actions_used -= 1
            hero.set_action_succeeded(False)
            return
        if self._console.remaining_cooldown(card) > 0:
            self._console.message("Специальная атака ещё восстанавливается.")
            self._console._actions_used -= 1
            hero.set_action_succeeded(False)
            return
        succeeded = hero.special_attack()
        hero.set_action_succeeded(succeeded)
        if not succeeded:
            self._console._actions_used -= 1


class _InputQueue(Queue[IEvent]):
    def __init__(self, console: "Console") -> None:
        super().__init__()
        self._console = console

    def get(self, block: bool = True, timeout: float | None = None) -> IEvent:
        """Return queued input or ask the player for an action."""
        if not self.empty() or not block or timeout is not None:
            return super().get(block, timeout)
        return self._console.next_event()


class Console(IModelSubscriber):
    """Provide a line-oriented interface for the game."""

    def __init__(
        self,
        input_stream: TextIO | None = None,
        output_stream: TextIO | None = None,
        saves_dir: str | Path = "saves",
    ) -> None:
        self._input = input_stream if input_stream is not None else sys.stdin
        self._output = output_stream if output_stream is not None else sys.stdout
        self._ansi = supports_ansi(self._output)
        self._color = self._ansi and "NO_COLOR" not in os.environ
        self._messages: list[str] = []
        self._input_lines: Queue[str | OSError | UnicodeError] = Queue()
        self._input_closed = False
        self._termination_requested = Event()
        self._input_thread = Thread(target=self._read_input, daemon=True)
        self._saves_dir = Path(saves_dir)
        self._game: Game | None = None
        self._events = _InputQueue(self)
        self._save_path: Path | None = None
        self._pending_save = False
        self._quit_requested = False
        self._ending_turn = False
        self._turn_tick: int | None = None
        self._actions_used = 0

    def run(self) -> None:
        """Run the main menu until the player exits."""
        self._input_thread.start()
        previous_handler = None
        if current_thread() is main_thread():
            previous_handler = signal.signal(signal.SIGTERM, self._handle_termination)
        try:
            self._run_menu()
        finally:
            if previous_handler is not None:
                signal.signal(signal.SIGTERM, previous_handler)

    def _run_menu(self) -> None:
        while True:
            self._write(
                "\n========================================\n"
                "               Б Ю Р О\n"
                "========================================\n"
                "  [1] Новая игра\n"
                "  [2] Загрузить игру\n"
                "  [0] Выход\n"
                "----------------------------------------"
            )
            choice = self._read("Ваш выбор > ")
            if choice is None or choice == "0":
                return
            if choice == "1":
                self._new_game()
            elif choice == "2":
                self._load_game()
            else:
                self._write("Неизвестный пункт меню.")

    def next_event(self) -> IEvent:
        """Read the next player action when the game requests it."""
        game = self._require_game()
        if self._turn_tick != game.get_ticks():
            if self._quit_requested:
                raise _QuitAtBoundary
            self._turn_tick = game.get_ticks()
            self._actions_used = 0
            self._ending_turn = False
            if self._pending_save:
                self._save_game()
                self._pending_save = False
        if self._quit_requested or self._ending_turn:
            self._actions_used += 1
            return _PassEvent()

        self._show_state()
        while True:
            command = self._read("\nКоманда > ")
            if command is None or command.lower() in {"q", "quit", "exit"}:
                self._quit_requested = True
                if self._actions_used == 0:
                    raise _QuitAtBoundary
                self._actions_used += 1
                self._write("Выход после завершения текущего хода.")
                return _PassEvent()
            event = self._parse_action(command.strip().lower())
            if event is not None:
                self._actions_used += 1
                return event

    def message(self, text: str) -> None:
        """Show feedback produced by a player action."""
        self._messages.append(text)
        self._messages = self._messages[-5:]
        self._write(text)

    def remaining_cooldown(self, card: IDCard) -> int:
        """Return the number of ticks until a card can be used."""
        return max(
            0, card.get_timeout() - (self._require_game().get_ticks() - card.get_tick_since())
        )

    def on_won(self) -> None:
        """Notify the player that the level is complete."""
        self.message("Уровень пройден.")

    def on_total_won(self) -> None:
        """Notify the player that the game is complete."""
        self._write("Победа! Вы получили паспорт.")

    def on_lost(self) -> None:
        """Notify the player that the hero has died."""
        self._write("Персонаж погиб. Сохранения этого прохождения недействительны.")

    def draw_passage(self, p: Position) -> None:
        """Accept map redraw notifications; the complete map is shown at the prompt."""

    def draw_object(self, p: ICellObject) -> None:
        """Accept object redraw notifications; the complete map is shown at the prompt."""

    def register_move(self, p: Position, d: Direction) -> None:
        """Accept movement notifications from the model."""

    def register_attack(self, p: Position, d: Direction) -> None:
        """Notify the player of an attack."""
        self.message("Атака.")

    def register_special_attack(self, p: Position, radius: int) -> None:
        """Notify the player of an area attack."""
        self.message("Специальная атака.")

    def show_things(self, ts: list[OneTimeBonus]) -> None:
        """Show the player's consumable items."""
        self._show_items(ts)

    def choose_from_cards(self, ics: list[IDCard]) -> int:
        """Ask the player to choose one of the offered cards."""
        if self._quit_requested:
            raise _QuitAtBoundary
        self._write("Выберите удостоверение:")
        for index, card in enumerate(ics, start=1):
            self._write(f"{index}. {self._card_description(card)}")
        while True:
            answer = self._read("Номер: ")
            if answer is None:
                self._quit_requested = True
                raise _QuitAtBoundary
            index = self._parse_index(answer, len(ics))
            if index is not None:
                return index
            self._write("Введите номер из списка.")

    def _new_game(self) -> None:
        try:
            config = GlobalConfig.get_instance()
            width, height = config.get_map_size()
            generator = CommonLevelGenerator(
                width,
                height,
                (2, 2),
                (1, 1),
                (2, 3),
                MonsterParamsGenerator(config.get_monster_param_pool()),
                MonsterStrategyGenerator([SimpleMonsterStrategy()]),
            )
            generator.boss_generator = BossLevelGenerator(
                width,
                height,
                2,
                MonsterParamsGenerator(config.get_boss_param_pool()),
                MonsterStrategyGenerator([SimpleMonsterStrategy()]),
                MonsterAttackGenerator(
                    [
                        config.get_boss_prizes(index).get_attack()
                        for index in range(config.get_boss_prize_pool_size())
                    ]
                ),
            )
            self._game = Game.create_new(generator, self._events, self)
        except (OSError, ValueError, KeyError) as error:
            self._write(f"Не удалось начать игру: {error}")
            return
        self._save_path = None
        self._play()

    def _load_game(self) -> None:
        try:
            saves = sorted(self._saves_dir.glob("*.json")) if self._saves_dir.is_dir() else []
        except OSError as error:
            self._write(f"Не удалось прочитать список сохранений: {error}")
            return
        if not saves:
            self._write("Сохранений нет.")
            return
        self._write("Сохранения:")
        for index, path in enumerate(saves, start=1):
            self._write(f"{index}. {path.name}")
        answer = self._read("Номер сохранения (0 — назад): ")
        if answer is None or answer == "0":
            return
        index = self._parse_index(answer, len(saves))
        if index is None:
            self._write("Неверный номер сохранения.")
            return
        try:
            self._game = GameLoader.load_from_file(saves[index], self._events, self)
        except (OSError, ValueError, KeyError, UnicodeError) as error:
            self._write(f"Не удалось загрузить сохранение: {error}")
            return
        self._save_path = saves[index]
        self._play()

    def _play(self) -> None:
        game = self._require_game()
        self._pending_save = False
        self._quit_requested = False
        self._ending_turn = False
        self._turn_tick = None
        self._actions_used = 0
        self._messages.clear()
        if getattr(game.get_level_generator(), "legacy_progress", False):
            self._messages.append(
                "Старое сохранение: номер уровня неизвестен, принят первый уровень секции."
            )
        try:
            game.run_game()
        except _QuitAtBoundary:
            self._quit_requested = True
        if self._quit_requested or self._pending_save:
            if game.has_lost_level():
                self._write("Персонаж погиб. Сохранение не выполнено.")
            else:
                self._save_game()
        self._game = None

    def _save_game(self) -> None:
        game = self._require_game()
        try:
            self._saves_dir.mkdir(parents=True, exist_ok=True)
            path = self._save_path
            if path is None:
                name = game.get_save_date().astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
                path = self._saves_dir / f"{name}.json"
                suffix = 1
                while path.exists():
                    path = self._saves_dir / f"{name}-{suffix}.json"
                    suffix += 1
            GameLoader.save_to_file(game, path)
            self._save_path = path
            self.message(f"Игра сохранена: {path}")
        except (OSError, ValueError) as error:
            self.message(f"Не удалось сохранить игру: {error}")

    def _parse_action(self, command: str) -> IEvent | None:
        game = self._require_game()
        directions = {
            "w": Direction.UP,
            "s": Direction.DOWN,
            "a": Direction.LEFT,
            "d": Direction.RIGHT,
        }
        if command in directions:
            return _MoveEvent(directions[command], self)
        if command in {"x", "attack"}:
            return _SpecialEvent(self)
        if command in {"end", "pass"}:
            self._ending_turn = True
            return _PassEvent()
        if command == "save":
            if self._actions_used == 0:
                self._save_game()
            else:
                self._pending_save = True
                self._write("Сохранение после завершения хода.")
        elif command in {"i", "items"}:
            self._show_items(list(game.get_hero().get_one_time_bonuses()))
        elif command in {"c", "cards"}:
            self._show_cards()
        elif command in {"f", "certificates"}:
            self._show_certificates()
        elif command.startswith("use "):
            items = list(game.get_hero().get_one_time_bonuses())
            index = self._parse_index(command[4:], len(items))
            if index is None:
                self._write("Неверный номер предмета.")
            else:
                return OneTimeBonusEvent(index)
        elif command.startswith("card "):
            self._select_card(command[5:])
        elif command in {"help", "?"}:
            self._show_help()
        else:
            self._write("Неизвестная команда.")
        return None

    def _show_state(self) -> None:
        game = self._require_game()
        card = game.get_hero().get_current_id_card()
        if card is None:
            cooldown = "не выбрано"
        else:
            remaining = self.remaining_cooldown(card)
            cooldown = "готова" if remaining == 0 else f"{remaining} ходов"
        if self._ansi:
            self._output.write("\x1b[2J\x1b[H")
        elif os.name == "nt" and self._output is sys.stdout and self._output.isatty():
            os.system("cls")
        self._write(render(game, self._actions_used, cooldown, self._messages, self._color))

    def _show_items(self, items: list[OneTimeBonus]) -> None:
        self._write("Предметы рюкзака:")
        if not items:
            self._write("Нет предметов.")
        for index, item in enumerate(items, start=1):
            self._write(f"{index}. {self._params_description(item.get_modifier())}")
        if items:
            self._write("Чтобы использовать предмет, введите use N, где N — его номер.")

    def _show_cards(self) -> None:
        hero = self._require_game().get_hero()
        cards = list(hero.get_id_cards())
        self._write("Удостоверения:")
        if not cards:
            self._write("Нет удостоверений.")
        for index, card in enumerate(cards, start=1):
            active = " (активно)" if card is hero.get_current_id_card() else ""
            self._write(f"{index}. {self._card_description(card)}{active}")

    def _show_certificates(self) -> None:
        certificates = list(self._require_game().get_hero().get_certificates())
        self._write("Справки:")
        if not certificates:
            self._write("Нет справок.")
        for index, certificate in enumerate(certificates, start=1):
            self._write(f"{index}. {self._params_description(certificate.get_params())}")

    def _select_card(self, value: str) -> None:
        hero = self._require_game().get_hero()
        index = self._parse_index(value, len(list(hero.get_id_cards())))
        if index is None:
            self._write("Неверный номер удостоверения.")
        elif hero.chose_id_card():
            self._write("Удостоверение уже выбрано.")
        else:
            hero.use_id_card(index)
            self._write("Удостоверение выбрано.")

    def _show_help(self) -> None:
        self._write(
            "\n  КОМАНДЫ\n"
            "  w / a / s / d — движение вверх / влево / вниз / вправо\n"
            "  x             — специальная атака с выбранным удостоверением\n"
            "  end           — закончить ход без оставшихся действий\n"
            "  i             — показать предметы; use N — использовать предмет номер N\n"
            "  c             — показать удостоверения; card N — выбрать удостоверение номер N\n"
            "  f             — показать справки\n"
            "  save          — сохранить игру; q — сохранить и выйти в меню\n"
            "  Вводите команды латинскими буквами и нажимайте Enter."
        )

    @staticmethod
    def _params_description(params: ActorParams) -> str:
        return (
            f"Здоровье: {params.health}, защита: {params.defence}, "
            f"атака: {params.attack}, скорость: {params.speed}"
        )

    def _card_description(self, card: IDCard) -> str:
        attack = card.get_attack()
        if isinstance(attack, CircleAttack):
            name = "атака по кругу"
        elif isinstance(attack, StraightAttack):
            name = "атака по прямой"
        elif isinstance(attack, WaveAttack):
            name = "атака волной"
        else:
            name = "специальная атака"
        return f"{name}, до готовности: {self.remaining_cooldown(card)} ходов"

    @staticmethod
    def _parse_index(value: str, count: int) -> int | None:
        try:
            index = int(value) - 1
        except ValueError:
            return None
        return index if 0 <= index < count else None

    def _require_game(self) -> Game:
        if self._game is None:
            raise RuntimeError("No active game")
        return self._game

    def _read(self, prompt: str) -> str | None:
        self._output.write(prompt)
        self._output.flush()
        if self._input_closed:
            return None
        while not self._termination_requested.is_set():
            try:
                line = self._input_lines.get(timeout=0.1)
            except Empty:
                continue
            except KeyboardInterrupt:
                self._write("")
                return None
            if isinstance(line, (OSError, UnicodeError)):
                raise line
            if line == "":
                self._input_closed = True
                return None
            return line.strip()
        return None

    def _read_input(self) -> None:
        while not self._termination_requested.is_set():
            try:
                line = self._input.readline()
            except (OSError, UnicodeError) as error:
                self._input_lines.put(error)
                return
            self._input_lines.put(line)
            if line == "":
                return

    def _handle_termination(self, signum: int, frame: object) -> None:
        self._termination_requested.set()

    def _write(self, text: str) -> None:
        print(text, file=self._output, flush=True)
