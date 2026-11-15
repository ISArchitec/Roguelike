from game import ActorParams
from positioning import Position, ICellObject


class Certificate(ICellObject):
    def __init__(self, params: ActorParams):
        self._params = params
        self._position = None

    def get_position(self) -> Position:
        return self._position

    def interact(self, force: int):
        pass

    def is_inactive(self) -> bool:
        # I have no idea, what does this mean
        return True

    def apply(self, hero_params: ActorParams) -> ActorParams:
        return self._params + hero_params
