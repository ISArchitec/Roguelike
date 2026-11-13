from game import ActorParams
from positioning import ICellObject, Position


class OneTimeBonus(ICellObject):
    def __init__(self, modifier: ActorParams):
        self._modifier = modifier
        self._position = None

    def get_modifier(self):
        return self._modifier

    def get_position(self) -> Position:
        return self._position

    def interact(self, force: int):
        pass

    def is_inactive(self) -> bool:
        # I have no idea, what does this mean
        return True
