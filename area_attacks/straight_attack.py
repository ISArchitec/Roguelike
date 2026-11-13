from positioning import IAreaAttack, IMap, Position, Direction


class StraightAttack(IAreaAttack):
    def __init__(self, length, direction: Direction, force: int):
        self._length = length
        self._force = force
        self._direction = direction

    def special_attack(self, map: IMap, position: Position):
        x = position.get_x()
        y = position.get_y()
        target_position = position
        for i in range(self._length):
            target_position = target_position.move(self._direction)
            map.interact_direct(target_position, self._force)
