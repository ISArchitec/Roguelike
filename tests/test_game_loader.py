import json
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue
from unittest.mock import MagicMock, patch

import pytest

from area_attacks import CircleAttack, StraightAttack, WaveAttack
from bonuses import Certificate, IDCard, OneTimeBonus
from game import ActorParams
from generation import ILevelGenerator
from hero import Hero
from map import Cell, Map
from monster_strategies.simple_monster_strategy import SimpleMonsterStrategy
from monsters import BossMonster, Monster
from play_cycle import GlobalConfig, IModelSubscriber
from play_cycle.game import Game
from positioning import Direction, Position
from serializing import GameLoader
from serializing.cell_object_loader import ICellObjectLoader
from serializing.save_data import SaveDataCodec


@pytest.fixture
def game():
    hero = Hero(
        ActorParams(20, 1, 4, 1), Position(0, 0), [OneTimeBonus(ActorParams(2, 0, 0, 0))], Queue()
    )
    card = IDCard(CircleAttack(1, 5), 4, Position(0, 0), 8)
    hero.add_id_card(card)
    hero.use_id_card(0)
    hero.add_certificate(Certificate(ActorParams(0, 0, 1, 0)))
    cells = [Cell.create_new(Position(x, y)) for y in range(2) for x in range(3)]
    cells[0].add_cell_object(hero)
    cells[5].make_wall()
    console = MagicMock(spec=IModelSubscriber)
    game_map = Map.create_from(3, 2, cells, hero, console)
    hero.set_map(game_map)
    enemy = Monster(ActorParams(10, 0, 3, 1), Position(1, 0), game_map, SimpleMonsterStrategy())
    boss = BossMonster(
        ActorParams(15, 1, 3, 1),
        Position(2, 0),
        game_map,
        SimpleMonsterStrategy(),
        WaveAttack([3, 2]),
    )
    game_map.add_object(enemy)
    game_map.add_object(boss)
    return Game(
        1,
        MagicMock(spec=ILevelGenerator),
        game_map,
        [enemy, boss],
        10,
        hero,
        console,
        2,
        1,
        False,
        False,
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def _load(data, game):
    config = MagicMock(spec=GlobalConfig)
    config.is_save_actual.return_value = True
    with patch("play_cycle.game.GlobalConfig.get_instance", return_value=config):
        return GameLoader.load_from(
            data, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


def test_round_trip_preserves_shared_objects_and_inventory(game, tmp_path):
    path = tmp_path / "save.json"
    GameLoader.save_to_file(game, path)
    data = SaveDataCodec.file_from_dict(json.loads(path.read_text(encoding="utf-8"))).snapshot
    restored = _load(data, game)
    cells = restored.get_map().get_cells()
    hero, enemy, boss = restored.get_actors()
    assert isinstance(hero, Hero)
    assert [cell.get_object() for cell in cells[:3]] == [hero, enemy, boss]
    assert restored.get_map().get_hero() is hero
    assert restored.get_ticks() == 10
    assert restored.get_section_passed() == 1
    assert hero.get_params().attack == 5
    assert len(list(hero.get_one_time_bonuses())) == 1
    assert len(list(hero.get_certificates())) == 1
    assert hero.get_current_id_card() is next(iter(hero.get_id_cards()))
    assert not hero.special_attack()


def test_save_omits_redundant_coordinates_and_inapplicable_fields(game, tmp_path):
    path = tmp_path / "save.json"
    GameLoader.save_to_file(game, path)
    snapshot = json.loads(path.read_text(encoding="utf-8"))["snapshot"]
    assert snapshot["version"] == 1
    assert "position" not in snapshot["map"]["cells"][0]
    assert snapshot["actors"][0]["position"] == {"x": 0, "y": 0}
    assert "inventory" not in snapshot["actors"][1]
    assert "attack" not in snapshot["actors"][1]
    assert "direction" not in snapshot["actors"][0]["inventory"]["id_cards"][0]["attack"]


def test_restores_actor_no_longer_on_map(game):
    enemy = game.get_actors()[1]
    enemy.interact(100)
    game.get_map().get_cells()[1].remove_cell_object(enemy)
    restored = _load(GameLoader.save_to(game), game)
    restored_enemy = restored.get_actors()[1]
    assert isinstance(restored_enemy, Monster)
    assert restored_enemy.is_inactive()
    assert (restored_enemy.get_position().get_x(), restored_enemy.get_position().get_y()) == (1, 0)
    assert restored.get_map().get_cells()[1].empty()


def test_enemies_are_constructed_with_restored_map(game):
    data = GameLoader.save_to(game)
    monster_init = Monster.__init__
    boss_init = BossMonster.__init__
    maps = []

    def init_monster(self, params, position, game_map, strategy):
        maps.append(game_map)
        monster_init(self, params, position, game_map, strategy)

    def init_boss(self, params, position, game_map, strategy, attack):
        maps.append(game_map)
        boss_init(self, params, position, game_map, strategy, attack)

    with (
        patch.object(Monster, "__init__", init_monster),
        patch.object(BossMonster, "__init__", init_boss),
    ):
        restored = _load(data, game)
    assert maps == [restored.get_map(), restored.get_map()]


def _game_with_reward(game, reward):
    game_map = game.get_map()
    for cell in game_map.get_cells():
        if cell.get_object() in game.get_actors()[1:]:
            cell.remove_cell_object(cell.get_object())
    reward.set_position(Position(0, 1))
    assert game_map.add_object(reward)
    return Game(
        game.get_section_passed(),
        game.get_level_generator(),
        game_map,
        [],
        game.get_ticks(),
        game.get_hero(),
        MagicMock(spec=IModelSubscriber),
        0,
        1,
        False,
        True,
        game.get_save_date(),
    )


def test_restored_reward_can_be_collected_after_enemies_are_defeated(game):
    reward = Certificate(ActorParams(0, 1, 0, 0))
    game = _game_with_reward(game, reward)
    restored = _load(GameLoader.save_to(game), game)
    restored.get_map().interact_direct(Position(0, 1), 0)
    assert len(list(restored.get_hero().get_certificates())) == 2
    assert restored.get_enemy_count() == 0
    assert restored.get_thing_got() == 0
    assert restored.get_map().get_cells()[3].empty()


@pytest.mark.parametrize(
    "attack", [CircleAttack(2, 4), StraightAttack(3, Direction.LEFT, 5), WaveAttack([1, 3])]
)
def test_attack_round_trip(attack):
    card = IDCard(attack, 3, Position(1, 2), 5)
    data = ICellObjectLoader.save_to(card)
    assert ICellObjectLoader.save_to(ICellObjectLoader.load_from(data)) == data


def test_load_from_file_restores_card_pickup_and_cooldown(game, tmp_path):
    position = Position(0, 1)
    reward = IDCard(CircleAttack(1, 7), 2, position, 9)
    game = _game_with_reward(game, reward)
    path = tmp_path / "save.json"
    GameLoader.save_to_file(game, path)
    config = MagicMock(spec=GlobalConfig)
    config.is_save_actual.return_value = True
    with patch("play_cycle.game.GlobalConfig.get_instance", return_value=config):
        restored = GameLoader.load_from_file(
            path, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )
    restored.get_map().interact_direct(position, 0)
    hero = restored.get_hero()
    assert len(list(hero.get_id_cards())) == 2
    hero.use_id_card(1)
    assert not hero.special_attack()


def test_corrupted_file_is_rejected(game, tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        GameLoader.load_from_file(
            path, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


def test_invalid_field_type_is_rejected(game, tmp_path):
    path = tmp_path / "save.json"
    GameLoader.save_to_file(game, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["snapshot"]["ticks"] = "ten"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid save value"):
        GameLoader.load_from_file(
            path, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


@pytest.mark.parametrize("field", ["snapshot", "checksum"])
def test_checksum_detects_corrupted_save(game, tmp_path, field):
    path = tmp_path / "save.json"
    GameLoader.save_to_file(game, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if field == "snapshot":
        data["snapshot"]["ticks"] += 1
    else:
        data["checksum"] = "0" * len(data["checksum"])
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        GameLoader.load_from_file(
            path, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


def test_save_without_checksum_is_rejected(game, tmp_path):
    path = tmp_path / "save.json"
    GameLoader.save_to_file(game, path)
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["checksum"]
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid fields"):
        GameLoader.load_from_file(
            path, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


def test_cannot_load_save_after_hero_dies(game, tmp_path):
    config_data = json.loads(Path("configs/config.json").read_text(encoding="utf-8"))
    config_data["actual_saves"] = []
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    config = GlobalConfig(config_path)
    config.register_save(game.get_save_date())
    save_path = tmp_path / "save.json"
    GameLoader.save_to_file(game, save_path)

    game.get_hero().interact(100)
    with patch("play_cycle.game.GlobalConfig.get_instance", return_value=config):
        game.run_game()

    reloaded_config = GlobalConfig(config_path)
    assert save_path.exists()
    assert not reloaded_config.is_save_actual(game.get_save_date())
    with (
        patch("play_cycle.game.GlobalConfig.get_instance", return_value=reloaded_config),
        pytest.raises(ValueError, match="no longer valid"),
    ):
        GameLoader.load_from_file(
            save_path, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


def test_invalidated_save_cannot_be_loaded(game):
    data = GameLoader.save_to(game)
    config = MagicMock(spec=GlobalConfig)
    config.is_save_actual.return_value = False
    with (
        patch("play_cycle.game.GlobalConfig.get_instance", return_value=config),
        pytest.raises(ValueError, match="no longer valid"),
    ):
        GameLoader.load_from(
            data, Queue(), MagicMock(spec=IModelSubscriber), game.get_level_generator()
        )


def test_invalid_reference_and_version_rejected(game):
    data = GameLoader.save_to(game)
    data.map.cells[0].actor_index = -1
    with pytest.raises(ValueError, match="actor reference"):
        _load(data, game)
    data.version = -1
    with pytest.raises(ValueError, match="version"):
        _load(data, game)


def test_failed_replace_preserves_previous_save(game, tmp_path):
    path = tmp_path / "save.json"
    path.write_text("previous", encoding="utf-8")
    with (
        patch("serializing.game_loader.os.replace", side_effect=OSError("write failed")),
        pytest.raises(OSError, match="write failed"),
    ):
        GameLoader.save_to_file(game, path)
    assert path.read_text(encoding="utf-8") == "previous"
    assert list(tmp_path.iterdir()) == [path]
