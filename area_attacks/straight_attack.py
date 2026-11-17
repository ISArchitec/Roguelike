from game import IAreaAttack
from positioning import Direction, IMap, Position


class StraightAttack(IAreaAttack):
    def __init__(self, length, direction: Direction, force: int):
        self._length = length
        self._force = force
        self._direction = direction

    def get_length(self) -> int:
        return self._length

    def get_force(self) -> int:
        return self._force

    def get_direction(self) -> Direction:
        return self._direction

    def special_attack(self, map: IMap, position: Position):
        target_position = position
        for _i in range(self._length):
            target_position = target_position.move(self._direction)
            map.interact_direct(target_position, self._force)
