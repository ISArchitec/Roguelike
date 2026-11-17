from collections.abc import Callable

from game import IAreaAttack
from positioning import Position, ICellObject, IMap


class IDCard(ICellObject):
    def __init__(self, attack: IAreaAttack, timeout: int, position: Position, tick_since: int):
        self._attack = attack
        self._timeout = timeout
        self._position = position
        self._tick_since = tick_since
        self._tick_getter: Callable[[], int] | None = None
        self._on_pickup: Callable[[], None] | None = None

    def get_position(self) -> Position:
        return self._position

    def set_position(self, position: Position) -> None:
        self._position = position

    def set_on_pickup(self, callback: Callable[[], None]) -> None:
        self._on_pickup = callback

    def interact(self, force: int):
        if self._on_pickup is not None:
            self._on_pickup()
            self._on_pickup = None

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
