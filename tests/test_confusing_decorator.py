from queue import Queue
from unittest.mock import MagicMock

import pytest

from game import ActorParams
from hero import Hero
from map import MapBuilder
from monster_strategies.simple_monster_strategy import SimpleMonsterStrategy
from monsters import Monster
from monsters.confusing_decorator import ConfusingDecorator
from monsters.enemy_interface import IEnemy
from play_cycle import IModelSubscriber
from positioning import Direction, IMap, Position


def make_confused_monster(remaining_turns=3):
    hero = Hero(ActorParams(20, 0, 1, 1), Position(0, 0), [], Queue())
    builder = MapBuilder(3, 3)
    builder.add_hero(hero)
    game_map = builder.to_map(MagicMock(spec=IModelSubscriber))
    monster = Monster(
        ActorParams(10, 0, 1, 1), Position(1, 1), game_map, SimpleMonsterStrategy()
    )
    confused = ConfusingDecorator(monster, remaining_turns)
    game_map.add_object(confused)
    return game_map, monster, confused


@pytest.mark.parametrize("remaining_turns", [1, 2, 3])
def test_remaining_turns_matches_constructor(remaining_turns):
    confused = ConfusingDecorator(MagicMock(spec=IEnemy), remaining_turns)

    assert confused.get_remaining_turns() == remaining_turns


@pytest.mark.parametrize("remaining_turns", [0, -1])
def test_nonpositive_remaining_turns_are_rejected(remaining_turns):
    with pytest.raises(ValueError, match="Remaining confusion turns must be positive"):
        ConfusingDecorator(MagicMock(spec=IEnemy), remaining_turns)


def test_default_confusion_lasts_three_turns():
    confused = ConfusingDecorator(MagicMock(spec=IEnemy))

    assert confused.get_remaining_turns() == 3


def test_unwrap_returns_original_enemy():
    enemy = MagicMock(spec=IEnemy)
    confused = ConfusingDecorator(enemy)

    assert confused.unwrap() is enemy


def test_get_position_returns_enemy_position():
    enemy = MagicMock(spec=IEnemy)
    position = Position(1, 2)
    enemy.get_position.return_value = position

    assert ConfusingDecorator(enemy).get_position() is position


def test_set_position_moves_underlying_enemy():
    enemy = MagicMock(spec=IEnemy)
    position = Position(2, 1)

    ConfusingDecorator(enemy).set_position(position)

    enemy.set_position.assert_called_once_with(position)


@pytest.mark.parametrize("inactive", [False, True])
def test_is_inactive_matches_enemy(inactive):
    enemy = MagicMock(spec=IEnemy)
    enemy.is_inactive.return_value = inactive

    assert ConfusingDecorator(enemy).is_inactive() is inactive


def test_get_strategy_returns_enemy_strategy():
    enemy = MagicMock(spec=IEnemy)
    strategy = SimpleMonsterStrategy()
    enemy.get_strategy.return_value = strategy

    assert ConfusingDecorator(enemy).get_strategy() is strategy


def test_get_params_returns_enemy_params():
    enemy = MagicMock(spec=IEnemy)
    params = ActorParams(10, 1, 2, 1)
    enemy.get_params.return_value = params

    assert ConfusingDecorator(enemy).get_params() is params


def test_get_map_returns_enemy_map():
    enemy = MagicMock(spec=IEnemy)
    game_map = MagicMock(spec=IMap)
    enemy.get_map.return_value = game_map

    assert ConfusingDecorator(enemy).get_map() is game_map


def test_interact_keeps_wrapper_when_enemy_remains_itself():
    enemy = MagicMock(spec=IEnemy)
    enemy.interact.return_value = enemy
    confused = ConfusingDecorator(enemy)

    assert confused.interact(4) is confused
    enemy.interact.assert_called_once_with(4)


def test_interact_returns_new_wrapper_when_confusion_is_retriggered():
    enemy = MagicMock(spec=IEnemy)
    replacement = ConfusingDecorator(enemy)
    enemy.interact.return_value = replacement
    confused = ConfusingDecorator(enemy, 2)

    assert confused.interact(4) is replacement
    enemy.interact.assert_called_once_with(4)


def test_step_moves_confused_monster_on_real_map():
    game_map, monster, confused = make_confused_monster(2)

    confused.step()

    position = monster.get_position()
    assert position != Position(1, 1)
    assert game_map.get_cells()[position.get_y() * 3 + position.get_x()].get_object() is confused


def test_step_surrounded_by_actors_neither_moves_nor_attacks():
    hero = Hero(ActorParams(20, 0, 1, 1), Position(1, 0), [], Queue())
    builder = MapBuilder(3, 3)
    builder.add_hero(hero)
    game_map = builder.to_map(MagicMock(spec=IModelSubscriber))
    strategy = SimpleMonsterStrategy()
    monster = Monster(ActorParams(10, 0, 5, 4), Position(1, 1), game_map, strategy)
    confused = ConfusingDecorator(monster, 2)
    game_map.add_object(confused)
    neighbors = [
        Monster(ActorParams(10, 0, 1, 1), position, game_map, strategy)
        for position in (Position(0, 1), Position(2, 1), Position(1, 2))
    ]
    for neighbor in neighbors:
        game_map.add_object(neighbor)

    confused.step()

    assert monster.get_position() == Position(1, 1)
    assert [actor.get_params().health for actor in (hero, *neighbors)] == [20, 10, 10, 10]


def test_step_uses_enemy_speed_for_each_move():
    enemy = MagicMock(spec=IEnemy)
    enemy.get_params.return_value = ActorParams(10, 0, 1, 2)
    game_map = MagicMock(spec=IMap)
    enemy.get_map.return_value = game_map
    confused = ConfusingDecorator(enemy, 2)

    confused.step()

    assert [call.args[0] for call in game_map.move.call_args_list] == [confused, confused]
    assert all(isinstance(call.args[1], Direction) for call in game_map.move.call_args_list)


def test_step_decrements_remaining_turns_once():
    enemy = MagicMock(spec=IEnemy)
    enemy.get_params.return_value = ActorParams(10, 0, 1, 2)
    enemy.get_map.return_value = MagicMock(spec=IMap)
    confused = ConfusingDecorator(enemy, 3)

    confused.step()

    assert confused.get_remaining_turns() == 2


def test_last_step_restores_original_enemy_on_real_map():
    game_map, monster, confused = make_confused_monster(1)

    confused.step()

    position = monster.get_position()
    assert game_map.get_cells()[position.get_y() * 3 + position.get_x()].get_object() is monster
    assert confused.get_remaining_turns() == 0
