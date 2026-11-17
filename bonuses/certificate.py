from collections.abc import Callable

from game import ActorParams
from positioning import Position, ICellObject


class Certificate(ICellObject):
    def __init__(self, params: ActorParams):
        self._params = params
        self._position = None
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

    def apply(self, hero_params: ActorParams) -> ActorParams:
        return self._params + hero_params
