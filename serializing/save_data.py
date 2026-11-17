from dataclasses import asdict, dataclass
from enum import StrEnum

from area_attacks import CircleAttack, StraightAttack, WaveAttack
from game import ActorParams, IAreaAttack
from positioning import Direction


class ActorType(StrEnum):
    """Supported actor types in a save."""

    HERO = "hero"
    MONSTER = "monster"
    BOSS = "boss"


class ObjectType(StrEnum):
    """Supported collectible types in a save."""

    CERTIFICATE = "certificate"
    ID_CARD = "id_card"


class AttackType(StrEnum):
    """Supported attack types in a save."""

    CIRCLE = "circle"
    STRAIGHT = "straight"
    WAVE = "wave"


class StrategyType(StrEnum):
    """Supported enemy strategies in a save."""

    SIMPLE = "simple"


@dataclass
class PositionData:
    """A position on the map."""

    x: int
    y: int


@dataclass
class ParamsData:
    """Actor statistics or item modifiers."""

    health: int
    defence: int
    attack: int
    speed: int

    @classmethod
    def from_params(cls, params: ActorParams) -> "ParamsData":
        """Capture actor parameters."""
        return cls(params.health, params.defence, params.attack, params.speed)

    def to_params(self) -> ActorParams:
        """Restore actor parameters."""
        return ActorParams(self.health, self.defence, self.attack, self.speed)


@dataclass
class AttackData:
    """Configuration of an area attack."""

    type: AttackType
    radius: int | None = None
    force: int | None = None
    length: int | None = None
    direction: str | None = None
    forces: list[int] | None = None

    @classmethod
    def from_attack(cls, attack: IAreaAttack) -> "AttackData":
        """Capture the configuration of a supported attack."""
        if type(attack) is CircleAttack:
            return cls(AttackType.CIRCLE, radius=attack.get_radius(), force=attack.get_force())
        if type(attack) is StraightAttack:
            return cls(
                AttackType.STRAIGHT,
                length=attack.get_length(),
                force=attack.get_force(),
                direction=attack.get_direction().name,
            )
        if type(attack) is WaveAttack:
            return cls(AttackType.WAVE, forces=list(attack.get_forces()))
        raise ValueError(f"Unsupported attack type: {type(attack).__name__}")

    def to_attack(self) -> IAreaAttack:
        """Restore a supported attack from its configuration."""
        if self.type is AttackType.CIRCLE:
            if self.radius is None or self.force is None or self.radius < 0 or self.force < 0:
                raise ValueError("Invalid circle attack")
            return CircleAttack(self.radius, self.force)
        if self.type is AttackType.STRAIGHT:
            if (
                self.length is None
                or self.force is None
                or self.direction is None
                or self.length < 0
                or self.force < 0
            ):
                raise ValueError("Invalid straight attack")
            try:
                return StraightAttack(self.length, Direction[self.direction], self.force)
            except KeyError as error:
                raise ValueError("Invalid attack direction") from error
        if self.type is AttackType.WAVE:
            if self.forces is None or any(force < 0 for force in self.forces):
                raise ValueError("Invalid wave attack")
            return WaveAttack(self.forces)
        raise ValueError(f"Unsupported attack type: {self.type!r}")


@dataclass
class ObjectData:
    """State of a collectible map object."""

    type: ObjectType
    position: PositionData | None
    params: ParamsData | None = None
    attack: AttackData | None = None
    timeout: int | None = None
    tick_since: int | None = None


@dataclass
class BonusData:
    """State of a one-time bonus."""

    modifier: ParamsData


@dataclass
class InventoryData:
    """Hero inventory and selected ID card."""

    one_timers: list[BonusData]
    id_cards: list[ObjectData]
    current_id: int | None
    certificates: list[ObjectData]


@dataclass
class ActorData:
    """State of a hero or an enemy."""

    type: ActorType
    params: ParamsData
    position: PositionData
    inventory: InventoryData | None = None
    strategy: StrategyType | None = None
    attack: AttackData | None = None


@dataclass
class CellData:
    """A map cell and its contents."""

    wall: bool
    actor_index: int | None = None
    object: ObjectData | None = None


@dataclass
class MapData:
    """Map dimensions and ordered cells."""

    width: int
    height: int
    cells: list[CellData]


@dataclass
class GameData:
    """Complete versioned game snapshot."""

    version: int
    generator: None
    section_passed: int
    ticks: int
    enemy_count: int
    thing_got: int
    is_section_end: bool
    reward_placed: bool
    save_date: str
    actors: list[ActorData]
    map: MapData


@dataclass
class SaveFileData:
    """A game snapshot and its checksum."""

    snapshot: GameData
    checksum: str


class SaveDataCodec:
    """Convert typed snapshots to and from JSON-compatible values."""

    @staticmethod
    def to_dict(data: GameData | SaveFileData) -> dict:
        """Convert a snapshot into JSON-compatible data."""
        return SaveDataCodec._omit_none(asdict(data))

    @staticmethod
    def file_from_dict(data: dict) -> SaveFileData:
        """Validate and decode a save file envelope."""
        try:
            SaveDataCodec._fields(data, {"snapshot", "checksum"})
            return SaveFileData(
                SaveDataCodec._game(data["snapshot"]), SaveDataCodec._string(data["checksum"])
            )
        except (KeyError, TypeError, AttributeError) as error:
            raise ValueError("Invalid save data") from error

    @staticmethod
    def _omit_none(value):
        if isinstance(value, dict):
            return {
                key: SaveDataCodec._omit_none(item)
                for key, item in value.items()
                if item is not None
            }
        if isinstance(value, list):
            return [SaveDataCodec._omit_none(item) for item in value]
        return value

    @staticmethod
    def _fields(data, required: set[str], optional: frozenset[str] = frozenset()) -> None:
        if (
            not isinstance(data, dict)
            or not required <= data.keys()
            or data.keys() - required - optional
        ):
            raise ValueError("Invalid fields in save data")

    @staticmethod
    def _integer(value) -> int:
        if type(value) is not int:
            raise ValueError("Invalid save value")
        return value

    @staticmethod
    def _boolean(value) -> bool:
        if type(value) is not bool:
            raise ValueError("Invalid save value")
        return value

    @staticmethod
    def _string(value) -> str:
        if type(value) is not str:
            raise ValueError("Invalid save value")
        return value

    @staticmethod
    def _list(value, loader) -> list:
        if not isinstance(value, list):
            raise ValueError("Invalid save list")
        return [loader(item) for item in value]

    @staticmethod
    def _position(data) -> PositionData:
        SaveDataCodec._fields(data, {"x", "y"})
        return PositionData(SaveDataCodec._integer(data["x"]), SaveDataCodec._integer(data["y"]))

    @staticmethod
    def _params(data) -> ParamsData:
        names = ("health", "defence", "attack", "speed")
        SaveDataCodec._fields(data, set(names))
        return ParamsData(*(SaveDataCodec._integer(data[name]) for name in names))

    @staticmethod
    def _attack(data) -> AttackData:
        SaveDataCodec._fields(
            data, {"type"}, frozenset({"radius", "force", "length", "direction", "forces"})
        )
        attack_type = AttackType(SaveDataCodec._string(data["type"]))
        required = {
            AttackType.CIRCLE: {"type", "radius", "force"},
            AttackType.STRAIGHT: {"type", "length", "direction", "force"},
            AttackType.WAVE: {"type", "forces"},
        }
        SaveDataCodec._fields(data, required[attack_type])
        return AttackData(
            attack_type,
            radius=SaveDataCodec._integer(data["radius"]) if "radius" in data else None,
            force=SaveDataCodec._integer(data["force"]) if "force" in data else None,
            length=SaveDataCodec._integer(data["length"]) if "length" in data else None,
            direction=SaveDataCodec._string(data["direction"]) if "direction" in data else None,
            forces=SaveDataCodec._list(data["forces"], SaveDataCodec._integer)
            if "forces" in data
            else None,
        )

    @staticmethod
    def _item(data) -> ObjectData:
        SaveDataCodec._fields(
            data, {"type"}, frozenset({"position", "params", "attack", "timeout", "tick_since"})
        )
        kind = ObjectType(SaveDataCodec._string(data["type"]))
        required = (
            {"type", "params"}
            if kind is ObjectType.CERTIFICATE
            else {"type", "attack", "timeout", "tick_since"}
        )
        SaveDataCodec._fields(data, required, frozenset({"position"}))
        return ObjectData(
            kind,
            SaveDataCodec._position(data["position"]) if "position" in data else None,
            params=SaveDataCodec._params(data["params"]) if "params" in data else None,
            attack=SaveDataCodec._attack(data["attack"]) if "attack" in data else None,
            timeout=SaveDataCodec._integer(data["timeout"]) if "timeout" in data else None,
            tick_since=SaveDataCodec._integer(data["tick_since"]) if "tick_since" in data else None,
        )

    @staticmethod
    def _bonus(data) -> BonusData:
        SaveDataCodec._fields(data, {"modifier"})
        return BonusData(SaveDataCodec._params(data["modifier"]))

    @staticmethod
    def _inventory(data) -> InventoryData:
        SaveDataCodec._fields(
            data, {"one_timers", "id_cards", "certificates"}, frozenset({"current_id"})
        )
        return InventoryData(
            SaveDataCodec._list(data["one_timers"], SaveDataCodec._bonus),
            SaveDataCodec._list(data["id_cards"], SaveDataCodec._item),
            SaveDataCodec._integer(data["current_id"]) if "current_id" in data else None,
            SaveDataCodec._list(data["certificates"], SaveDataCodec._item),
        )

    @staticmethod
    def _actor(data) -> ActorData:
        common = {"type", "params", "position"}
        SaveDataCodec._fields(data, common, frozenset({"inventory", "strategy", "attack"}))
        kind = ActorType(SaveDataCodec._string(data["type"]))
        required = common | ({"inventory"} if kind is ActorType.HERO else {"strategy"})
        if kind is ActorType.BOSS:
            required.add("attack")
        SaveDataCodec._fields(data, required)
        return ActorData(
            kind,
            SaveDataCodec._params(data["params"]),
            SaveDataCodec._position(data["position"]),
            inventory=SaveDataCodec._inventory(data["inventory"]) if "inventory" in data else None,
            strategy=StrategyType(SaveDataCodec._string(data["strategy"]))
            if "strategy" in data
            else None,
            attack=SaveDataCodec._attack(data["attack"]) if "attack" in data else None,
        )

    @staticmethod
    def _cell(data) -> CellData:
        SaveDataCodec._fields(data, {"wall"}, frozenset({"actor_index", "object"}))
        return CellData(
            SaveDataCodec._boolean(data["wall"]),
            actor_index=SaveDataCodec._integer(data["actor_index"])
            if "actor_index" in data
            else None,
            object=SaveDataCodec._item(data["object"]) if "object" in data else None,
        )

    @staticmethod
    def _map(data) -> MapData:
        SaveDataCodec._fields(data, {"width", "height", "cells"})
        return MapData(
            SaveDataCodec._integer(data["width"]),
            SaveDataCodec._integer(data["height"]),
            SaveDataCodec._list(data["cells"], SaveDataCodec._cell),
        )

    @staticmethod
    def _game(data) -> GameData:
        required = {
            "version",
            "section_passed",
            "ticks",
            "enemy_count",
            "thing_got",
            "is_section_end",
            "reward_placed",
            "save_date",
            "actors",
            "map",
        }
        SaveDataCodec._fields(data, required)
        return GameData(
            SaveDataCodec._integer(data["version"]),
            None,
            SaveDataCodec._integer(data["section_passed"]),
            SaveDataCodec._integer(data["ticks"]),
            SaveDataCodec._integer(data["enemy_count"]),
            SaveDataCodec._integer(data["thing_got"]),
            SaveDataCodec._boolean(data["is_section_end"]),
            SaveDataCodec._boolean(data["reward_placed"]),
            SaveDataCodec._string(data["save_date"]),
            SaveDataCodec._list(data["actors"], SaveDataCodec._actor),
            SaveDataCodec._map(data["map"]),
        )
