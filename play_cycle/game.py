from queue import Queue
from copy import deepcopy
from datetime import datetime, timezone
from random import randrange, sample

from bonuses import OneTimeBonus
from game import IActor
from generation import ILevelGenerator
from hero import Hero, IEvent
from map import Map
from monsters import IEnemy
from play_cycle import GlobalConfig, IModelSubscriber
from positioning import ICellObject, Position

_MAX_SECTION_PASSED = 5

class Game:
    def __init__(self, section_passed: int, level_generator: ILevelGenerator, map: Map, actors: list[IActor],
                 ticks: int, hero: Hero, console: IModelSubscriber, enemy_count: int, thing_got: int,
                 is_section_end: bool, reward_placed: bool, save_date: datetime):
        if section_passed < 0 or ticks < 0:
            raise ValueError("Section and tick counters cannot be negative")
        self._section_passed = section_passed
        self._level_generator = level_generator
        self._map = map
        self._hero = hero
        self._actors = [hero] + [actor for actor in actors]
        self._ticks = ticks
        self._is_stopped = False
        self._console = console
        self._enemy_count = enemy_count
        self._thing_got = thing_got
        self._is_section_end = is_section_end
        self._reward_placed = reward_placed
        self._save_date = save_date
        self._map.set_on_terminate_object(self._count_down_on_terminate)
        for card in self._hero.get_id_cards():
            card.set_tick_getter(self.get_ticks)

    @staticmethod
    def create_new(level_generator: ILevelGenerator, event_queue: Queue[IEvent], console: IModelSubscriber) -> "Game":
        config = GlobalConfig.get_instance()
        params = config.get_initial_hero_params()
        one_timers = Game._create_initial_inventory(config)
        hero = Hero(params, Position(0, 0), one_timers, event_queue)
        map, enemies, is_section_end = level_generator.generate_level(0, hero, console)
        hero.set_map(map)
        save_date = datetime.now(timezone.utc)
        game = Game(0, level_generator, map, enemies, 0, hero, console, len(enemies), 1, is_section_end, False, save_date)
        config.register_save(save_date)
        return game

    @staticmethod
    def create_from(section_passed: int, level_generator: ILevelGenerator, map: Map, actors: list[IActor],
                    ticks: int, hero: Hero, console: IModelSubscriber, enemy_count: int, thing_got: int,
                    is_section_end: bool, reward_placed: bool, save_date: datetime) -> "Game":
        if not GlobalConfig.get_instance().is_save_actual(save_date):
            raise ValueError("Save is no longer valid or was never registered")
        return Game(section_passed, level_generator, map, actors, ticks, hero, console, enemy_count, thing_got, is_section_end, reward_placed, save_date)

    def run_game(self) -> None:
        while not self._is_stopped:
            if self.has_lost_level():
                GlobalConfig.get_instance().invalidate_save(self._save_date)
                self._console.on_lost()
                return
            if self.has_won_level():
                if self.has_won_totally():
                    self._console.on_total_won()
                    return
                self._console.on_won()
                self._advance_level()
            elif self._enemy_count == 0 and not self._reward_placed:
                self._place_level_reward()
            self._tick()

    def has_won_level(self) -> bool:
        return self._enemy_count == 0 and self._thing_got == 0

    def has_lost_level(self) -> bool:
        return self._hero.is_inactive()

    def has_won_totally(self) -> bool:
        return (self.has_won_level() and self._is_section_end
                and self._section_passed + 1 >= _MAX_SECTION_PASSED)

    def stop(self) -> None:
        self._is_stopped = True

    def get_ticks(self) -> int:
        return self._ticks

    def get_save_date(self) -> datetime:
        return self._save_date

    def _tick(self) -> None:
        for actor in self._actors:
            if isinstance(actor, ICellObject) and actor.is_inactive(): # TODO:
                continue
            actor.step()
        self._ticks += 1
        self._map.draw()

    def _count_down_on_terminate(self) -> None:
        if self._enemy_count == 0:
            if self._thing_got == 0:
                raise ValueError("nothing to count")
            self._thing_got -= 1
        else:
            self._enemy_count -= 1

    @staticmethod
    def _create_initial_inventory(config: GlobalConfig) -> list[OneTimeBonus]:
        pool_size = config.get_initial_thing_pool_size()
        return [deepcopy(config.get_special_thing(randrange(pool_size)))
                for _ in range(config.get_initial_thing_count())]

    def _place_level_reward(self) -> None:
        config = GlobalConfig.get_instance()
        if self._is_section_end:
            pool_size = config.get_boss_prize_pool_size()
            if pool_size < 2:
                raise ValueError("At least two boss prizes are required")
            cards = [deepcopy(config.get_boss_prizes(index)) for index in sample(range(pool_size), 2)]
            selected_index = self._console.choose_from_cards(cards)
            if not 0 <= selected_index < len(cards):
                raise ValueError("Selected card index is outside the offered choices")
            reward = cards[selected_index]
            reward.set_tick_getter(self.get_ticks)
            reward.set_on_pickup(lambda: self._hero.add_id_card(reward))
        else:
            pool_size = config.get_certificate_pool_size()
            if pool_size == 0:
                raise ValueError("Certificate pool cannot be empty")
            reward = deepcopy(config.get_certificate(randrange(pool_size)))
            reward.set_on_pickup(lambda: self._hero.add_certificate(reward))
        self._place_randomly(reward)
        self._reward_placed = True

    def _place_randomly(self, obj: ICellObject) -> None:
        width, height = GlobalConfig.get_instance().get_map_size()
        for index in sample(range(width * height), width * height):
            obj.set_position(Position(index % width, index // width))
            if self._map.add_object(obj):
                return
        raise ValueError("No free cell is available for the level reward")

    def _advance_level(self) -> None:
        section_passed = self._section_passed
        if self._is_section_end:
            section_passed += 1
        new_map, enemies, is_section_end = self._level_generator.generate_level(
            section_passed, self._hero, self._console)
        new_map.set_on_terminate_object(self._count_down_on_terminate)
        self._hero.set_map(new_map)
        self._section_passed = section_passed
        self._is_section_end = is_section_end
        self._map = new_map
        self._actors = [self._hero] + list(enemies)
        self._enemy_count = len(enemies)
        self._thing_got = 1
        self._reward_placed = False
