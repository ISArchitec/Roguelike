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
        """Return the card's map position, or None when it is off the map."""
        return self._position

    def get_attack(self) -> IAreaAttack:
        """Return the card's special attack."""
        return self._attack

    def get_timeout(self) -> int:
        """Return the attack cooldown in turns."""
        return self._timeout

    def get_tick_since(self) -> int:
        """Return the turn number of the last attack use."""
        return self._tick_since

    def set_position(self, position: Position) -> None:
        """Set the card's position on the map."""
        self._position = position

    def set_on_pickup(self, callback: Callable[[], None]) -> None:
        """Set the callback invoked when the card is first picked up."""
        self._on_pickup = callback

    def interact(self, force: int) -> ICellObject:
        """Invoke the pickup callback once and return this card."""
        if self._on_pickup is not None:
            self._on_pickup()
            self._on_pickup = None
        return self

    def is_inactive(self) -> bool:
        """Return whether the card has no pending pickup callback."""
        return self._on_pickup is None

    def special_attack(self, map: IMap, position: Position) -> bool:
        """Use the special attack from the given position if its cooldown has elapsed."""
        if self._tick_getter is None:
            raise RuntimeError("Card tick getter has not been set")
        tick = self._tick_getter()
        if tick - self._tick_since < self._timeout:
            return False
        self._attack.special_attack(map, position)
        self._tick_since = tick
        return True

    def set_tick_getter(self, callback: Callable[[], int]) -> None:
        """Set the current-turn provider used to check the attack cooldown."""
        self._tick_getter = callback
