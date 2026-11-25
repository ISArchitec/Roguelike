from collections.abc import Callable

from game import ActorParams
from positioning import ICellObject, Position


class Certificate(ICellObject):
    def __init__(self, params: ActorParams):
        self._params = params
        self._position = None
        self._on_pickup: Callable[[], None] | None = None

    def get_position(self) -> Position | None:
        return self._position

    def get_params(self) -> ActorParams:
        return self._params

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

    def apply(self, hero_params: ActorParams) -> ActorParams:
        return self._params + hero_params
