import json
import os
import signal
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from game import ActorParams, IActor
from hero import Hero
from map import Cell, Map
from play_cycle import GlobalConfig
from play_cycle.game import Game
from positioning import Position
from view import Console
from view.renderer import supports_ansi


@pytest.fixture
def configured_game(tmp_path, monkeypatch):
    data = json.loads(Path("configs/config.json").read_text(encoding="utf-8"))
    data["actual_saves"] = []
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(data), encoding="utf-8")
    config = GlobalConfig(config_path)
    monkeypatch.setattr(GlobalConfig, "_config", config)
    return config_path


class TerminalOutput(StringIO):
    def isatty(self):
        """Simulate output connected to a terminal."""
        return True


@pytest.mark.parametrize("reason", ["redirected", "dumb"])
def test_color_disabled_when_terminal_does_not_support_it(monkeypatch, reason):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm")
    output: StringIO = TerminalOutput()
    if reason == "redirected":
        output = StringIO()
    elif reason == "dumb":
        monkeypatch.setenv("TERM", "dumb")
    assert not supports_ansi(output)


def test_no_color_still_clears_terminal(configured_game, tmp_path, monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    output = TerminalOutput()
    with (
        patch("view.console.supports_ansi", return_value=True),
        patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]),
    ):
        Console(StringIO("1\nq\n0\n"), output, tmp_path / "saves").run()

    assert "\x1b[2J\x1b[H" in output.getvalue()
    assert "\x1b[96m" not in output.getvalue()


def test_redirected_game_output_does_not_contain_terminal_control_codes(configured_game, tmp_path):
    output = StringIO()
    console = Console(StringIO("1\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    assert "\x1b[" not in output.getvalue()
    assert "Здоровье: 20" in output.getvalue()


def test_terminal_draws_in_color_and_keeps_feedback_in_next_frame(
    configured_game, tmp_path, monkeypatch
):
    monkeypatch.delenv("NO_COLOR", raising=False)
    output = TerminalOutput()
    with (
        patch("view.console.supports_ansi", return_value=True),
        patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]),
    ):
        Console(StringIO("1\na\nq\n0\n"), output, tmp_path / "saves").run()

    frames = output.getvalue().split("\x1b[2J\x1b[H")
    assert len(frames) >= 3
    assert "\x1b[96m" in frames[1]
    assert "Движение невозможно." in frames[-1]


def test_game_screen_fits_narrow_terminal(configured_game, tmp_path):
    output = TerminalOutput()
    with (
        patch("view.console.supports_ansi", return_value=True),
        patch("view.renderer.shutil.get_terminal_size", return_value=os.terminal_size((50, 24))),
        patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]),
    ):
        Console(StringIO("1\nq\n0\n"), output, tmp_path / "saves").run()

    frame = output.getvalue().split("\x1b[2J\x1b[H")[1].split("Команда >")[0]
    assert len(frame.splitlines()) < 24
    assert "Здоровье: 20" in frame
    assert "WASD" in frame


def test_start_save_and_reload_game(configured_game, tmp_path):
    output = StringIO()
    console = Console(StringIO("1\nq\n2\n1\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    saves = list((tmp_path / "saves").glob("*.json"))
    assert len(saves) == 1
    assert output.getvalue().count("Игра сохранена:") == 2
    assert "Сохранения:" in output.getvalue()
    assert json.loads(saves[0].read_text(encoding="utf-8"))["snapshot"]["ticks"] == 0


def test_termination_saves_game_at_turn_boundary(configured_game, tmp_path):
    original_tick = Game._tick

    def terminate_at_tick(game):
        signal.raise_signal(signal.SIGTERM)
        return original_tick(game)

    console = Console(StringIO("1\n"), StringIO(), tmp_path / "saves")
    with (
        patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]),
        patch.object(Game, "_tick", terminate_at_tick),
    ):
        console.run()

    save_path = next((tmp_path / "saves").glob("*.json"))
    assert json.loads(save_path.read_text(encoding="utf-8"))["snapshot"]["ticks"] == 0


def test_quit_mid_turn_saves_after_full_tick(configured_game, tmp_path):
    data = json.loads(configured_game.read_text(encoding="utf-8"))
    data["initial_hero_params"]["speed"] = 2
    configured_game.write_text(json.dumps(data), encoding="utf-8")
    GlobalConfig._config = GlobalConfig(configured_game)
    output = StringIO()
    console = Console(StringIO("1\nw\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    save_path = next((tmp_path / "saves").glob("*.json"))
    snapshot = json.loads(save_path.read_text(encoding="utf-8"))["snapshot"]
    assert snapshot["ticks"] == 1
    assert snapshot["actors"][0]["position"] == {"x": 0, "y": 1}
    assert "Выход после завершения текущего хода." in output.getvalue()


def test_loading_without_saved_games_reports_empty_list(tmp_path):
    output = StringIO()
    Console(StringIO("2\n0\n"), output, tmp_path / "saves").run()
    assert "Сохранений нет." in output.getvalue()


def test_inventory_shows_how_to_use_items(configured_game, tmp_path):
    output = StringIO()
    console = Console(StringIO("1\ni\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    assert "введите use N" in output.getvalue()
    assert "пошаговая игра" not in output.getvalue()


def test_game_screen_shows_map_status_and_controls(configured_game, tmp_path):
    data = json.loads(configured_game.read_text(encoding="utf-8"))
    data["object_view"]["hero"] = "H"
    configured_game.write_text(json.dumps(data), encoding="utf-8")
    GlobalConfig._config = GlobalConfig(configured_game)
    output = StringIO()
    console = Console(StringIO("1\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    screen = output.getvalue()
    assert "-H-" in screen and "\\|/" in screen
    assert "x: 1\u201315 / 20" in screen
    assert "ОБОЗНАЧЕНИЯ" not in screen
    assert "card N выбрать удостоверение" in screen
    assert "Здоровье: 20" in screen
    assert "Действий: 1" in screen
    assert "WASD" in screen


def test_map_view_follows_hero(configured_game, tmp_path):
    output = StringIO()
    commands = "1\n" + "w\n" * 4 + "d\n" * 9 + "q\n0\n"
    console = Console(StringIO(commands), output, tmp_path / "saves")
    with (
        patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 18, 4, 19, 5]),
        patch("monsters.monster.Monster.step"),
    ):
        console.run()

    assert "x: 3\u201317 / 20" in output.getvalue()


def test_generated_monster_is_visible_on_map(configured_game, tmp_path):
    output = StringIO()
    console = Console(StringIO("1\nw\nw\nw\nq\n0\n"), output, tmp_path / "saves")
    with (
        patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 2, 4, 3, 5]),
        patch("monsters.monster.Monster.step"),
    ):
        console.run()

    assert "|m|" in output.getvalue()


def test_invalid_move_and_missing_card_are_reported(configured_game, tmp_path):
    output = StringIO()
    console = Console(StringIO("1\na\nx\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    assert "Движение невозможно." in output.getvalue()
    assert "Удостоверение не выбрано." in output.getvalue()


def test_failed_actions_do_not_advance_tick(configured_game, tmp_path):
    output = StringIO()
    console = Console(StringIO("1\na\nx\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    save = next((tmp_path / "saves").glob("*.json"))
    assert json.loads(save.read_text(encoding="utf-8"))["snapshot"]["ticks"] == 0


def test_manual_save_waits_for_turn_boundary(configured_game, tmp_path):
    data = json.loads(configured_game.read_text(encoding="utf-8"))
    data["initial_hero_params"]["speed"] = 2
    configured_game.write_text(json.dumps(data), encoding="utf-8")
    GlobalConfig._config = GlobalConfig(configured_game)
    output = StringIO()
    console = Console(StringIO("1\nw\nsave\nend\nq\n0\n"), output, tmp_path / "saves")
    with patch("random.randint", side_effect=[2, 1, 2, 6, 2, 4, 5, 4, 6, 5]):
        console.run()

    save_path = next((tmp_path / "saves").glob("*.json"))
    snapshot = json.loads(save_path.read_text(encoding="utf-8"))["snapshot"]
    assert snapshot["ticks"] == 1
    assert snapshot["actors"][0]["position"] == {"x": 0, "y": 1}
    assert "Сохранение после завершения хода." in output.getvalue()


def test_quit_mid_turn_processes_hero_death(configured_game, tmp_path):
    save_date = datetime(2026, 1, 1, tzinfo=UTC)
    config = GlobalConfig._config
    assert config is not None

    def create_game(generator, events, console):
        hero = Hero(ActorParams(20, 0, 1, 2), Position(0, 0), [], events)
        cells = [Cell.create_new(Position(0, y)) for y in range(2)]
        cells[0].add_cell_object(hero)
        game_map = Map.create_from(1, 2, cells, hero, console)
        hero.set_map(game_map)
        enemy = MagicMock(spec=IActor)
        enemy.step.side_effect = lambda: hero.interact(100)
        config.register_save(save_date)
        return Game(
            0, generator, game_map, [enemy], 0, hero, console, 1, 1, False, False, save_date
        )

    output = StringIO()
    console = Console(StringIO("1\nw\nq\n0\n"), output, tmp_path / "saves")
    with patch("view.console.Game.create_new", side_effect=create_game):
        console.run()

    assert not config.is_save_actual(save_date)
    assert "Персонаж погиб" in output.getvalue()
    assert not (tmp_path / "saves").exists()
