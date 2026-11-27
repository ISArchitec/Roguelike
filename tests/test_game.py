from datetime import UTC, datetime, timedelta
from queue import Queue
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from area_attacks import CircleAttack
from bonuses import Certificate, IDCard, OneTimeBonus
from game import ActorParams
from generation import ILevelGenerator
from hero import Hero
from map import Cell, Map
from monsters import IEnemy
from play_cycle import GlobalConfig, IModelSubscriber
from play_cycle.game import Game
from positioning import Position

SAVE_DATE = datetime(2026, 1, 2, tzinfo=UTC)


@pytest.fixture
def dependencies():
    config = MagicMock(spec=GlobalConfig)
    config.is_save_actual.return_value = True
    config.get_initial_hero_params.return_value = ActorParams(20, 1, 5, 1)
    config.get_initial_thing_count.return_value = 2
    config.get_initial_thing_pool_size.return_value = 1
    config.get_special_thing.return_value = OneTimeBonus(ActorParams(1, 0, 0, 0))
    config.get_map_size.return_value = (2, 2)
    config.get_certificate_pool_size.return_value = 1
    config.get_certificate.return_value = Certificate(ActorParams(1, 0, 0, 0))
    cards = [IDCard(CircleAttack(1, 5), 1, Position(0, 0), 0) for _ in range(2)]
    config.get_boss_prize_pool_size.return_value = len(cards)
    config.get_boss_prizes.side_effect = cards.__getitem__
    hero = MagicMock(spec=Hero)
    hero.is_inactive.return_value = False
    hero.get_id_cards.return_value = []
    enemy = MagicMock(spec=IEnemy)
    enemy.is_inactive.return_value = False
    game_map = MagicMock(spec=Map)
    game_map.add_object.return_value = True
    console = MagicMock(spec=IModelSubscriber)
    console.choose_from_cards.return_value = 0
    generator = MagicMock(spec=ILevelGenerator)
    generator.generate_level.return_value = (game_map, [enemy], False)
    with patch("play_cycle.game.GlobalConfig.get_instance", return_value=config):
        yield SimpleNamespace(
            config=config,
            hero=hero,
            enemy=enemy,
            game_map=game_map,
            console=console,
            generator=generator,
        )


@pytest.fixture
def build_game(dependencies):
    def build(**overrides):
        args = {
            "section_passed": 0,
            "level_generator": dependencies.generator,
            "map": dependencies.game_map,
            "actors": [dependencies.enemy],
            "ticks": 0,
            "hero": dependencies.hero,
            "console": dependencies.console,
            "enemy_count": 1,
            "thing_got": 1,
            "is_section_end": False,
            "reward_placed": False,
            "save_date": SAVE_DATE,
        }
        args.update(overrides)
        return Game.create_from(**args)

    return build


def test_new_game_registers_save(dependencies):
    game = Game.create_new(dependencies.generator, Queue(), dependencies.console)
    dependencies.config.register_save.assert_called_once_with(game.get_save_date())
    assert game.get_save_date().utcoffset() == timedelta(0)


def test_new_game_generates_first_level(dependencies):
    Game.create_new(dependencies.generator, Queue(), dependencies.console)
    section, _, console = dependencies.generator.generate_level.call_args.args
    assert (section, console) == (0, dependencies.console)


def test_new_game_copies_initial_inventory(dependencies):
    Game.create_new(dependencies.generator, Queue(), dependencies.console)
    hero = dependencies.generator.generate_level.call_args.args[1]
    bonuses = list(hero.get_one_time_bonuses())
    assert len(bonuses) == 2
    assert (
        len(
            {id(bonuses[0]), id(bonuses[1]), id(dependencies.config.get_special_thing.return_value)}
        )
        == 3
    )


def test_restore_rejects_invalid_save(dependencies, build_game):
    dependencies.config.is_save_actual.return_value = False
    with pytest.raises(ValueError, match="Save is no longer valid or was never registered"):
        build_game()


def test_restore_keeps_counters_and_date(build_game):
    game = build_game(ticks=42)
    assert game.get_ticks() == 42
    assert game.get_save_date() == SAVE_DATE


@pytest.mark.parametrize("overrides", [{"ticks": -1}, {"section_passed": -1}])
def test_rejects_negative_counters(build_game, overrides):
    with pytest.raises(ValueError, match="Section and tick counters cannot be negative"):
        build_game(**overrides)


@pytest.mark.parametrize(
    "enemies, reward_left, expected", [(1, 1, False), (0, 1, False), (1, 0, False), (0, 0, True)]
)
def test_level_victory_requires_enemies_and_reward(build_game, enemies, reward_left, expected):
    assert build_game(enemy_count=enemies, thing_got=reward_left).has_won_level() is expected


@pytest.mark.parametrize(
    "section, is_end, expected", [(3, True, False), (4, False, False), (4, True, True)]
)
def test_total_victory_requires_final_section(build_game, section, is_end, expected):
    game = build_game(section_passed=section, is_section_end=is_end, enemy_count=0, thing_got=0)
    assert game.has_won_totally() is expected


def test_stopped_game_does_not_tick(dependencies, build_game):
    game = build_game()
    game.stop()
    game.run_game()
    assert game.get_ticks() == 0


def test_tick_steps_actors(dependencies, build_game):
    game = build_game()
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    dependencies.hero.step.assert_called_once_with()
    dependencies.enemy.step.assert_called_once_with()


def test_tick_updates_time_and_draws(dependencies, build_game):
    game = build_game(ticks=7)
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    assert game.get_ticks() == 8
    dependencies.game_map.draw.assert_called_once_with()


def test_tick_skips_inactive_enemy(dependencies, build_game):
    dependencies.enemy.is_inactive.return_value = True
    game = build_game()
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    dependencies.enemy.step.assert_not_called()


def test_loss_invalidates_save(dependencies, build_game):
    dependencies.hero.is_inactive.return_value = True
    game = build_game()
    game.run_game()
    dependencies.config.invalidate_save.assert_called_once_with(SAVE_DATE)
    dependencies.console.on_lost.assert_called_once_with()


def test_final_victory_does_not_generate_next_level(dependencies, build_game):
    game = build_game(section_passed=4, is_section_end=True, enemy_count=0, thing_got=0)
    game.run_game()
    dependencies.console.on_total_won.assert_called_once_with()
    dependencies.generator.generate_level.assert_not_called()


@pytest.mark.parametrize("is_section_end, next_section", [(False, 1), (True, 2)])
def test_victory_generates_next_level(dependencies, build_game, is_section_end, next_section):
    game = build_game(section_passed=1, is_section_end=is_section_end, enemy_count=0, thing_got=0)
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    dependencies.console.on_won.assert_called_once_with()
    dependencies.generator.generate_level.assert_called_once_with(
        next_section, dependencies.hero, dependencies.console
    )


def test_next_level_replaces_map_and_enemies(dependencies, build_game):
    new_map = MagicMock(spec=Map)
    new_enemy = MagicMock(spec=IEnemy)
    new_enemy.is_inactive.return_value = False
    dependencies.generator.generate_level.return_value = (new_map, [new_enemy], False)
    game = build_game(enemy_count=0, thing_got=0)
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    dependencies.hero.set_map.assert_called_once_with(new_map)
    new_enemy.step.assert_called_once_with()


def test_actor_replacements_follow_latest_object(dependencies, build_game):
    dependencies.hero.get_position.return_value = Position(0, 0)
    dependencies.enemy.get_position.return_value = Position(1, 0)
    game_map = Map.create_from(
        2,
        1,
        [
            Cell.create_from(Position(0, 0), dependencies.hero, False),
            Cell.create_from(Position(1, 0), dependencies.enemy, False),
        ],
        dependencies.hero,
        dependencies.console,
    )
    game = build_game(map=game_map)
    first = MagicMock(spec=IEnemy)
    first.get_position.return_value = Position(1, 0)
    second = MagicMock(spec=IEnemy)
    second.get_position.return_value = Position(1, 0)

    game_map.replace_object(dependencies.enemy, first)
    game_map.replace_object(first, second)
    assert game.get_actors() == (dependencies.hero, second)


def test_next_level_rebuilds_actor_replacement_index(dependencies, build_game):
    dependencies.hero.get_position.return_value = Position(0, 0)
    new_enemy = MagicMock(spec=IEnemy)
    new_enemy.get_position.return_value = Position(1, 0)
    new_enemy.is_inactive.return_value = False
    new_map = Map.create_from(
        2,
        1,
        [
            Cell.create_from(Position(0, 0), dependencies.hero, False),
            Cell.create_from(Position(1, 0), new_enemy, False),
        ],
        dependencies.hero,
        dependencies.console,
    )
    dependencies.generator.generate_level.return_value = (new_map, [new_enemy], False)
    game = build_game(enemy_count=0, thing_got=0)
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    replacement = MagicMock(spec=IEnemy)
    replacement.get_position.return_value = Position(1, 0)

    assert new_map.replace_object(new_enemy, replacement)
    assert game.get_actors() == (dependencies.hero, replacement)


def test_next_level_resets_victory(dependencies, build_game):
    game = build_game(enemy_count=0, thing_got=0)
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    assert not game.has_won_level()


def test_termination_callback_counts_enemy_then_reward(dependencies, build_game):
    game = build_game()
    terminate = dependencies.game_map.set_on_terminate_object.call_args.args[0]
    terminate()
    assert not game.has_won_level()
    terminate()
    assert game.has_won_level()


def test_reward_placement_retries_busy_cell(dependencies, build_game):
    dependencies.game_map.add_object.side_effect = [False, True]
    game = build_game(enemy_count=0)
    dependencies.hero.step.side_effect = game.stop
    game.run_game()
    assert dependencies.game_map.add_object.call_count == 2


def test_reward_is_placed_only_once(dependencies, build_game):
    game = build_game(enemy_count=0)

    def stop_after_two_ticks():
        if game.get_ticks() == 1:
            game.stop()

    dependencies.hero.step.side_effect = stop_after_two_ticks
    game.run_game()
    dependencies.game_map.add_object.assert_called_once()


def test_full_map_rejects_reward(dependencies, build_game):
    dependencies.game_map.add_object.return_value = False
    game = build_game(enemy_count=0)
    with pytest.raises(ValueError, match="No free cell is available"):
        game.run_game()
    assert dependencies.game_map.add_object.call_count == 4
