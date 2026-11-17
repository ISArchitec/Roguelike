from unittest.mock import MagicMock, call, patch

import pytest

from game import ActorParams, IAreaAttack
from generation import (
    BossLevelGenerator,
    CommonLevelGenerator,
    ILevelGenerator,
    MonsterAttackGenerator,
    MonsterParamsGenerator,
    MonsterStrategyGenerator,
)
from hero import Hero
from map import Map
from monsters import BossMonster, IMonsterStrategy, Monster
from play_cycle import IModelSubscriber
from positioning import Position


def make_hero(position=(5, 5)):
    hero = MagicMock(spec=Hero)
    hero.get_position.return_value = Position(*position)
    hero.set_position.side_effect = lambda pos: setattr(hero.get_position, "return_value", pos)
    return hero


@pytest.mark.parametrize(
    "section_number, base, expected",
    [
        pytest.param(
            1,
            ActorParams(10, 2, 3, 4),
            (10, 2, 3, 4),
            id="first-section-keeps-base-stats",
        ),
        pytest.param(
            3,
            ActorParams(10, 2, 3, 4),
            (30, 6, 9, 4),
            id="later-section-scales-health-defence-attack",
        ),
    ],
)
def test_monster_params_generator_scales_selected_params(section_number, base, expected):
    generator = MonsterParamsGenerator([base])

    with patch("generation.monster_params_generator.random.choice", return_value=base):
        params = generator.generate_monster_params(section_number)

    assert (params.health, params.defence, params.attack, params.speed) == expected
    assert (base.health, base.defence, base.attack, base.speed) == (10, 2, 3, 4)


def test_monster_params_generator_chooses_from_pool():
    first = ActorParams(10, 1, 1, 1)
    second = ActorParams(20, 2, 2, 2)
    generator = MonsterParamsGenerator([first, second])

    with patch("generation.monster_params_generator.random.choice", return_value=second) as choice:
        params = generator.generate_monster_params(2)

    choice.assert_called_once_with([first, second])
    assert (params.health, params.defence, params.attack, params.speed) == (40, 4, 4, 2)


def test_monster_strategy_generator_returns_selected_strategy():
    strategies = [MagicMock(spec=IMonsterStrategy), MagicMock(spec=IMonsterStrategy)]
    generator = MonsterStrategyGenerator(list(strategies))

    with patch(
        "generation.monster_strategy_generator.random.choice", return_value=strategies[1]
    ) as choice:
        strategy = generator.generate_monster_strategy()

    choice.assert_called_once_with(strategies)
    assert strategy is strategies[1]


def test_monster_attack_generator_returns_selected_attack():
    attacks = [MagicMock(spec=IAreaAttack), MagicMock(spec=IAreaAttack)]
    generator = MonsterAttackGenerator(list(attacks))

    with patch(
        "generation.monster_attack_generator.random.choice", return_value=attacks[0]
    ) as choice:
        attack = generator.generate_monster_attack()

    choice.assert_called_once_with(attacks)
    assert attack is attacks[0]


def test_common_level_generator_builds_map_places_hero_and_spawns_enemies():
    console = MagicMock(spec=IModelSubscriber)
    hero = make_hero()
    params = ActorParams(5, 1, 2, 3)
    strategy = MagicMock(spec=IMonsterStrategy)
    params_gen = MagicMock(spec=MonsterParamsGenerator)
    params_gen.generate_monster_params.return_value = params
    strategy_gen = MagicMock(spec=MonsterStrategyGenerator)
    strategy_gen.generate_monster_strategy.return_value = strategy
    generator = CommonLevelGenerator(
        width=60,
        height=40,
        hallway_width_range=(3, 3),
        corner_size_range=(2, 2),
        enemies_range=(2, 2),
        params_gen=params_gen,
        strategy_gen=strategy_gen,
    )

    with patch(
        "generation.common_level_generator.random.randint",
        side_effect=[3, 2, 2, 15, 6, 10, 1, 2, 1, 3],
    ):
        game_map, enemies, section_finished = generator.generate_level(4, hero, console)

    assert isinstance(generator, ILevelGenerator)
    assert isinstance(game_map, Map)
    assert section_finished is False
    assert len(enemies) == 2
    assert all(isinstance(enemy, Monster) for enemy in enemies)
    hero.set_position.assert_called_once()
    assert (
        hero.set_position.call_args.args[0].get_x(),
        hero.set_position.call_args.args[0].get_y(),
    ) == (0, 0)
    assert params_gen.generate_monster_params.call_args_list == [call(4), call(4)]
    assert strategy_gen.generate_monster_strategy.call_count == 2
    assert {enemy.get_params() for enemy in enemies} == {params}
    assert {enemy.get_strategy() for enemy in enemies} == {strategy}
    actual_positions = [e.get_position() for e in enemies]
    reference_positions = [Position(1, 2), Position(1, 3)]
    assert all(actual_positions[i] == reference_positions[i] for i in range(2))


def test_boss_level_generator_builds_map_places_hero_and_spawns_boss():
    console = MagicMock(spec=IModelSubscriber)
    hero = make_hero()
    params = ActorParams(30, 4, 7, 2)
    strategy = MagicMock(spec=IMonsterStrategy)
    attack = MagicMock(spec=IAreaAttack)
    params_gen = MagicMock(spec=MonsterParamsGenerator)
    params_gen.generate_monster_params.return_value = params
    strategy_gen = MagicMock(spec=MonsterStrategyGenerator)
    strategy_gen.generate_monster_strategy.return_value = strategy
    attack_gen = MagicMock(spec=MonsterAttackGenerator)
    attack_gen.generate_monster_attack.return_value = attack
    generator = BossLevelGenerator(
        width=11,
        height=9,
        hallway_width=3,
        params_gen=params_gen,
        strategy_gen=strategy_gen,
        attack_gen=attack_gen,
    )

    game_map, enemies, section_finished = generator.generate_level(2, hero, console)

    assert isinstance(generator, ILevelGenerator)
    assert isinstance(game_map, Map)
    assert section_finished is True
    assert len(enemies) == 1
    boss = enemies[0]
    assert isinstance(boss, BossMonster)
    assert (boss.get_position().get_x(), boss.get_position().get_y()) == (5, 8)
    assert boss.get_params() is params
    assert boss.get_strategy() is strategy
    assert boss.get_attack() is attack
    hero.set_position.assert_called_once()
    assert (
        hero.set_position.call_args.args[0].get_x(),
        hero.set_position.call_args.args[0].get_y(),
    ) == (5, 0)
    params_gen.generate_monster_params.assert_called_once_with(2)
    strategy_gen.generate_monster_strategy.assert_called_once_with()
    attack_gen.generate_monster_attack.assert_called_once_with()
