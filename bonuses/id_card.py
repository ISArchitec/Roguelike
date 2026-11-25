from collections.abc import Callable

from game import IAreaAttack
from positioning import ICellObject, IMap, Position


class IDCard(ICellObject):
    def __init__(
        self, attack: IAreaAttack, timeout: int, position: Position | None, tick_since: int
    ):
        self._attack = attack
        self._timeout = timeout
        self._position = position
        self._tick_since = tick_since
        self._tick_getter: Callable[[], int] | None = None
        self._on_pickup: Callable[[], None] | None = None

    def get_position(self) -> Position | None:
        return self._position

    def get_attack(self) -> IAreaAttack:
        return self._attack

    def get_timeout(self) -> int:
        return self._timeout

    def get_tick_since(self) -> int:
        return self._tick_since

    def set_position(self, position: Position) -> None:
        self._position = position

    def set_on_pickup(self, callback: Callable[[], None]) -> None:
        self._on_pickup = callback

    def interact(self, force: int) -> ICellObject:
        if self._on_pickup is not None:
            self._on_pickup()
            self._on_pickup = None
        return self

    def is_inactive(self) -> bool:
        return self._on_pickup is None

    def special_attack(self, map: IMap, position: Position) -> bool:
        if self._tick_getter is None:
            raise RuntimeError("Card tick getter has not been set")
        tick = self._tick_getter()
        if tick - self._tick_since < self._timeout:
            return False
        self._attack.special_attack(map, position)
        self._tick_since = tick
        return True

    def set_tick_getter(self, callback: Callable[[], int]) -> None:
        self._tick_getter = callback
