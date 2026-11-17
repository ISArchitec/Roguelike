import json
from datetime import datetime, timedelta, timezone, tzinfo
from unittest.mock import patch

import pytest

from play_cycle.global_config import GlobalConfig


PARAMS = {"health": 20, "defence": 1, "attack": 5, "speed": 1}
DATE = datetime(2026, 1, 2, 12, 30, 45, 123456, tzinfo=timezone.utc)


@pytest.fixture
def config_data():
    return {
        "map_size": [3, 2],
        "initial_hero_params": dict(PARAMS),
        "monster_param_pool": [dict(PARAMS)],
        "boss_param_pool": [dict(PARAMS)],
        "object_view": {"hero": "@"},
        "boss_id_cards": [
            {"attack": {"type": "circle", "radius": 1, "force": 5}, "timeout": 3, "position": [0, 0], "tick_since": 0},
            {"attack": {"type": "straight", "length": 3, "direction": "UP", "force": 5}, "timeout": 3, "position": [0, 0], "tick_since": 0},
            {"attack": {"type": "wave", "forces": [5, 3, 1]}, "timeout": 4, "position": [0, 0], "tick_since": 0},
        ],
        "certificates": [dict(PARAMS)],
        "initial_thing_pool": [dict(PARAMS)],
        "initial_thing_count": 1,
    }


@pytest.fixture
def write_config(tmp_path):
    def write(data):
        path = tmp_path / "config.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path
    return write


@pytest.mark.parametrize("field", [
    "map_size", "initial_hero_params", "monster_param_pool", "boss_param_pool",
    "object_view", "boss_id_cards", "certificates", "initial_thing_pool", "initial_thing_count",
])
def test_load_missing_field(config_data, write_config, field):
    del config_data[field]
    with pytest.raises(KeyError, match=field):
        GlobalConfig(write_config(config_data))


@pytest.mark.parametrize("text", ["", "{", '{"map_size": [3, 2],}', "not json"])
def test_load_invalid_json(tmp_path, text):
    path = tmp_path / "config.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        GlobalConfig(path)


def test_load_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        GlobalConfig(tmp_path / "missing.json")


@pytest.mark.parametrize("field, value, error, message", [
    ("actual_saves", {}, ValueError, "Actual saves must be a list"),
    ("actual_saves", None, ValueError, "Actual saves must be a list"),
    ("actual_saves", "2026-01-02", ValueError, "Actual saves must be a list"),
    ("actual_saves", ["invalid"], ValueError, "Invalid isoformat"),
    ("actual_saves", ["2026-01-02T12:30:45"], ValueError, "Save date must include a timezone"),
    ("actual_saves", [42], TypeError, "fromisoformat"),
    ("map_size", [1], ValueError, "not enough values"),
    ("map_size", [1, 2, 3], ValueError, "too many values"),
    ("object_view", {"hero": 42}, ValueError, "Object view must be a string"),
    ("object_view", {"unknown": "?"}, KeyError, "unknown"),
])
def test_load_invalid_field(config_data, write_config, field, value, error, message):
    config_data[field] = value
    with pytest.raises(error, match=message):
        GlobalConfig(write_config(config_data))


@pytest.mark.parametrize("path, name", [
    (("map_size", 0), "map width"),
    (("map_size", 1), "map height"),
    (("initial_thing_count",), "initial thing count"),
    (("boss_id_cards", 0, "timeout"), "card timeout"),
    (("boss_id_cards", 0, "tick_since"), "card tick"),
    (("boss_id_cards", 0, "position", 0), "card x"),
    (("boss_id_cards", 0, "position", 1), "card y"),
    (("boss_id_cards", 0, "attack", "radius"), "attack radius"),
    (("boss_id_cards", 0, "attack", "force"), "attack force"),
    (("boss_id_cards", 1, "attack", "length"), "attack length"),
    (("boss_id_cards", 1, "attack", "force"), "attack force"),
    (("boss_id_cards", 2, "attack", "forces", 0), "attack force"),
])
@pytest.mark.parametrize("value", [-1, True, 1.5, "1", None])
def test_load_invalid_integer(config_data, write_config, path, name, value):
    target = config_data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError, match=f"Invalid {name}"):
        GlobalConfig(write_config(config_data))


@pytest.mark.parametrize("axis", [0, 1])
def test_load_zero_dimension(config_data, write_config, axis):
    config_data["map_size"][axis] = 0
    with pytest.raises(ValueError, match="Invalid map"):
        GlobalConfig(write_config(config_data))


@pytest.mark.parametrize("pool", ["initial_hero_params", "monster_param_pool", "boss_param_pool", "certificates", "initial_thing_pool"])
@pytest.mark.parametrize("field", ["health", "defence", "attack", "speed"])
def test_load_invalid_actor_param(config_data, write_config, pool, field):
    params = config_data[pool] if pool == "initial_hero_params" else config_data[pool][0]
    params[field] = True
    with pytest.raises(ValueError, match=f"Invalid {field}"):
        GlobalConfig(write_config(config_data))


@pytest.mark.parametrize("attack, error, message", [
    ({"type": "unknown"}, ValueError, "Unknown attack type"),
    ({"type": "straight", "length": 1, "direction": "DIAGONAL", "force": 1}, KeyError, "DIAGONAL"),
    ({"type": "circle", "force": 1}, KeyError, "radius"),
    ({"radius": 1, "force": 1}, KeyError, "type"),
])
def test_load_invalid_attack(config_data, write_config, attack, error, message):
    config_data["boss_id_cards"][0]["attack"] = attack
    with pytest.raises(error, match=message):
        GlobalConfig(write_config(config_data))


@pytest.mark.parametrize("count, empty_pool, valid", [(0, True, True), (0, False, True), (1, True, False), (1, False, True)])
def test_load_initial_things(config_data, write_config, count, empty_pool, valid):
    config_data["initial_thing_count"] = count
    if empty_pool:
        config_data["initial_thing_pool"] = []
    path = write_config(config_data)
    if not valid:
        with pytest.raises(ValueError, match="Initial thing pool cannot be empty"):
            GlobalConfig(path)
    else:
        config = GlobalConfig(path)
        assert config.get_initial_thing_count() == count
        assert config.get_initial_thing_pool_size() == (0 if empty_pool else 1)


@pytest.mark.parametrize("dates, expected", [
    ([], False),
    ([DATE.isoformat()], True),
    ([DATE.astimezone(timezone(timedelta(hours=3))).isoformat()], True),
    ([DATE.isoformat(), DATE.isoformat()], True),
])
def test_load_actual_saves(config_data, write_config, dates, expected):
    config_data["actual_saves"] = dates
    assert GlobalConfig(write_config(config_data)).is_save_actual(DATE) is expected


def test_load_missing_actual_saves(config_data, write_config):
    assert not GlobalConfig(write_config(config_data)).is_save_actual(DATE)


@pytest.fixture
def saved_config(config_data, write_config):
    path = write_config(config_data)
    return GlobalConfig(path), path


@pytest.mark.parametrize("offset", [-5, 0, 3])
def test_register_save_updates_memory(saved_config, offset):
    config, _ = saved_config
    config.register_save(DATE.astimezone(timezone(timedelta(hours=offset))))
    assert config.is_save_actual(DATE)


@pytest.mark.parametrize("offset", [-5, 0, 3])
def test_register_save_persists_utc(saved_config, offset):
    config, path = saved_config
    config.register_save(DATE.astimezone(timezone(timedelta(hours=offset))))
    assert json.loads(path.read_text(encoding="utf-8"))["actual_saves"] == [DATE.isoformat(timespec="microseconds")]


def test_register_save_survives_reload(saved_config):
    config, path = saved_config
    config.register_save(DATE)
    assert GlobalConfig(path).is_save_actual(DATE)


@pytest.mark.parametrize("dates", [(DATE, DATE + timedelta(seconds=1)), (DATE + timedelta(seconds=1), DATE)])
def test_register_save_keeps_previous_dates(saved_config, dates):
    config, path = saved_config
    for date in dates:
        config.register_save(date)
    assert json.loads(path.read_text(encoding="utf-8"))["actual_saves"] == [DATE.isoformat(), (DATE + timedelta(seconds=1)).isoformat()]


def test_register_save_preserves_other_settings(saved_config, config_data):
    config, path = saved_config
    config.register_save(DATE)
    stored = json.loads(path.read_text(encoding="utf-8"))
    del stored["actual_saves"]
    assert stored == config_data


@pytest.mark.parametrize("offset", [0, 3])
def test_register_save_rejects_duplicate(saved_config, offset):
    config, path = saved_config
    config.register_save(DATE)
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Save date is already registered"):
        config.register_save(DATE.astimezone(timezone(timedelta(hours=offset))))
    assert path.read_bytes() == before


class UnknownTimezone(tzinfo):
    def utcoffset(self, dt):
        return None


@pytest.mark.parametrize("date", [DATE.replace(tzinfo=None), DATE.replace(tzinfo=UnknownTimezone())])
def test_register_save_rejects_missing_timezone(saved_config, date):
    config, path = saved_config
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Save date must include a timezone"):
        config.register_save(date)
    assert path.read_bytes() == before


@pytest.fixture(params=["temporary-file", "serialization", "replace"])
def failed_registration(request, saved_config):
    config, path = saved_config
    before = path.read_bytes()
    targets = {
        "temporary-file": "play_cycle.global_config.NamedTemporaryFile",
        "serialization": "play_cycle.global_config.json.dump",
        "replace": "play_cycle.global_config.os.replace",
    }
    with patch(targets[request.param], side_effect=OSError("write failed")):
        with pytest.raises(OSError, match="write failed"):
            config.register_save(DATE)
    return config, path, before


def test_failed_registration_preserves_file(failed_registration):
    _, path, before = failed_registration
    assert path.read_bytes() == before


def test_failed_registration_does_not_register_date(failed_registration):
    config, _, _ = failed_registration
    assert not config.is_save_actual(DATE)


def test_failed_registration_removes_temporary_file(failed_registration):
    _, path, _ = failed_registration
    assert list(path.parent.iterdir()) == [path]
