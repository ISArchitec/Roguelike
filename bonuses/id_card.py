from positioning import IAreaAttack, Position, ICellObject, IMap


class IDCard(ICellObject):
    def __init__(self, attack: IAreaAttack, timeout: int, position: Position, tick_since: int):
        self._attack = attack
        self._timeout = timeout
        self._position = position
        self._tick_since = tick_since

    def get_position(self) -> Position:
        return self._position

    def interact(self, force: int):
        pass

    def is_inactive(self) -> bool:
        # I have no idea, what does this mean
        return True

    def special_attack(self, map: IMap, position: Position):
        self._attack.special_attack(map, position)

    def set_tick_getter(self, callback):
        # I have no idea, what does this mean
        pass
