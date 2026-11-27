import json
import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from area_attacks import CircleAttack, StraightAttack, WaveAttack
from bonuses import Certificate, IDCard, OneTimeBonus
from game import ActorParams, IAreaAttack
from hero import Hero
from monster_strategies.simple_monster_strategy import SimpleMonsterStrategy
from monsters import BossMonster, IMonsterStrategy, Monster
from positioning import Direction, ICellObject, Position

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "config.json"


class GlobalConfig:
    _config: "GlobalConfig | None" = None

    def __init__(self, path: str | Path = _DEFAULT_CONFIG_PATH):
        self._path = Path(path).resolve()
        self._load(self._path)

    @staticmethod
    def get_instance() -> "GlobalConfig":
        """Return the shared configuration instance, creating it on first use."""
        if GlobalConfig._config is None:
            GlobalConfig._config = GlobalConfig()
        return GlobalConfig._config

    def get_map_size(self) -> tuple[int, int]:
        """Return the configured map width and height."""
        return self._map_size

    def get_initial_hero_params(self) -> ActorParams:
        """Return the hero's initial parameters."""
        return self._initial_hero_params

    def get_monster_param_pool(self) -> list[ActorParams]:
        """Return the pool of parameters for generated monsters."""
        return self._monster_param_pool

    def get_boss_param_pool(self) -> list[ActorParams]:
        """Return the pool of parameters for generated bosses."""
        return self._boss_param_pool

    def get_object_view(self, obj: ICellObject) -> str:
        """Return the display symbol for the object's exact type."""
        return self._object_view[type(obj)]

    def get_boss_strategies(self) -> Iterator[str]:
        """Return an iterator over available boss strategy names."""
        return iter(self._boss_strategies)

    def get_boss_strategy(self, name: str) -> Callable[[], IMonsterStrategy]:
        """Return the boss strategy constructor for a name."""
        return self._boss_strategies[name]

    def get_boss_prizes(self, index: int) -> IDCard:
        """Return the boss reward ID card at the given index."""
        return self._boss_id_cards[index]

    def get_boss_prize_pool_size(self) -> int:
        """Return the number of boss reward ID cards."""
        return len(self._boss_id_cards)

    def get_certificate(self, index: int) -> Certificate:
        """Return the reward certificate at the given index."""
        return self._certificates[index]

    def get_certificate_pool_size(self) -> int:
        """Return the number of reward certificates."""
        return len(self._certificates)

    def get_special_thing(self, index: int) -> OneTimeBonus:
        """Return the initial one-time bonus at the given index."""
        return self._initial_thing_pool[index]

    def get_initial_thing_count(self) -> int:
        """Return the number of one-time bonuses initially given to the hero."""
        return self._initial_thing_count

    def get_initial_thing_pool_size(self) -> int:
        """Return the size of the initial bonus pool."""
        return len(self._initial_thing_pool)

    def register_save(self, save_date: datetime) -> None:
        """Register a timezone-aware save date as valid."""
        if save_date.tzinfo is None or save_date.utcoffset() is None:
            raise ValueError("Save date must include a timezone")
        if save_date in self._actual_saves:
            raise ValueError("Save date is already registered")
        self._write_actual_saves(self._actual_saves | {save_date.astimezone(UTC)})

    def is_save_actual(self, save_date: datetime) -> bool:
        """Return whether the save date is registered as valid."""
        return save_date in self._actual_saves

    def invalidate_save(self, save_date: datetime) -> None:
        """Remove the save date from the set of valid dates."""
        if save_date in self._actual_saves:
            self._write_actual_saves(self._actual_saves - {save_date})

    def _write_actual_saves(self, actual_saves: set[datetime]) -> None:
        with self._path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        data["actual_saves"] = sorted(
            date.isoformat(timespec="microseconds") for date in actual_saves
        )
        temporary_path = None
        try:
            with NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self._path.parent, delete=False
            ) as stream:
                temporary_path = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
            os.replace(temporary_path, self._path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        self._actual_saves = actual_saves

    def _load(self, path: Path) -> None:
        with path.open(encoding="utf-8") as stream:
            data = json.load(stream)
        actual_saves = data.get("actual_saves", [])
        if not isinstance(actual_saves, list):
            raise ValueError("Actual saves must be a list of dates")
        self._actual_saves: set[datetime] = set()
        for value in actual_saves:
            save_date = datetime.fromisoformat(value)
            if save_date.tzinfo is None or save_date.utcoffset() is None:
                raise ValueError("Save date must include a timezone")
            self._actual_saves.add(save_date.astimezone(UTC))
        width, height = data["map_size"]
        self._map_size = (
            self._read_int(width, "map width", 1),
            self._read_int(height, "map height", 1),
        )
        self._initial_hero_params = self._read_params(data["initial_hero_params"])
        self._monster_param_pool = [
            self._read_params(params) for params in data["monster_param_pool"]
        ]
        self._boss_param_pool = [self._read_params(params) for params in data["boss_param_pool"]]
        object_types = {
            "hero": Hero,
            "monster": Monster,
            "boss_monster": BossMonster,
            "certificate": Certificate,
            "id_card": IDCard,
        }
        self._object_view = {}
        for name, view in data["object_view"].items():
            if not isinstance(view, str):
                raise ValueError("Object view must be a string")
            self._object_view[object_types[name]] = view
        self._boss_strategies = {"simple": SimpleMonsterStrategy}
        self._boss_id_cards = [self._read_card(card) for card in data["boss_id_cards"]]
        self._certificates = [
            Certificate(self._read_params(params)) for params in data["certificates"]
        ]
        self._initial_thing_pool = [
            OneTimeBonus(self._read_params(params)) for params in data["initial_thing_pool"]
        ]
        self._initial_thing_count = self._read_int(
            data["initial_thing_count"], "initial thing count", 0
        )
        if self._initial_thing_count > 0 and not self._initial_thing_pool:
            raise ValueError(
                "Initial thing pool cannot be empty when initial thing count is positive"
            )

    @staticmethod
    def _read_int(value, name: str, minimum: int | None = None) -> int:
        if type(value) is not int or (minimum is not None and value < minimum):
            raise ValueError(f"Invalid {name}: {value!r}")
        return value

    @staticmethod
    def _read_params(data: dict) -> ActorParams:
        return ActorParams(
            *(
                GlobalConfig._read_int(data[name], name)
                for name in ("health", "defence", "attack", "speed")
            )
        )

    @staticmethod
    def _read_attack(data: dict) -> IAreaAttack:
        match data["type"]:
            case "circle":
                return CircleAttack(
                    GlobalConfig._read_int(data["radius"], "attack radius", 0),
                    GlobalConfig._read_int(data["force"], "attack force", 0),
                )
            case "straight":
                return StraightAttack(
                    GlobalConfig._read_int(data["length"], "attack length", 0),
                    Direction[data["direction"]],
                    GlobalConfig._read_int(data["force"], "attack force", 0),
                )
            case "wave":
                return WaveAttack(
                    [GlobalConfig._read_int(force, "attack force", 0) for force in data["forces"]]
                )
            case _:
                raise ValueError(f"Unknown attack type: {data['type']!r}")

    @staticmethod
    def _read_card(data: dict) -> IDCard:
        x, y = data["position"]
        position = Position(
            GlobalConfig._read_int(x, "card x", 0), GlobalConfig._read_int(y, "card y", 0)
        )
        return IDCard(
            GlobalConfig._read_attack(data["attack"]),
            GlobalConfig._read_int(data["timeout"], "card timeout", 0),
            position,
            GlobalConfig._read_int(data["tick_since"], "card tick", 0),
        )
