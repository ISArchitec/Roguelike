from collections.abc import Callable

from game import ActorParams
from positioning import ICellObject, Position


class Certificate(ICellObject):
    def __init__(self, params: ActorParams):
        self._params = params
        self._position = None
        self._on_pickup: Callable[[], None] | None = None

    def get_position(self) -> Position | None:
        """Return the certificate's map position, or None before placement."""
        return self._position

    def get_params(self) -> ActorParams:
        """Return the stat modifiers this certificate adds to the hero."""
        return self._params

    def set_position(self, position: Position) -> None:
        """Set the certificate's position on the map."""
        self._position = position

    def set_on_pickup(self, callback: Callable[[], None]) -> None:
        """Set the callback invoked when the certificate is first picked up."""
        self._on_pickup = callback

    def interact(self, force: int) -> ICellObject:
        """Invoke the pickup callback once and return this certificate."""
        if self._on_pickup is not None:
            self._on_pickup()
            self._on_pickup = None
        return self

    def is_inactive(self) -> bool:
        """Return whether the certificate has no pending pickup callback."""
        return self._on_pickup is None

    def apply(self, hero_params: ActorParams) -> ActorParams:
        """Return the hero's stats with this certificate's modifiers added."""
        return self._params + hero_params
