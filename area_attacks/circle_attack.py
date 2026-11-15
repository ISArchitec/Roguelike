from positioning import IAreaAttack, IMap, Position


class CircleAttack(IAreaAttack):
    def __init__(self, radius: int, force: int):
        self._radius = radius
        self._force = force

    def special_attack(self, map: IMap, position: Position):
        x = position.get_x()
        y = position.get_y()
        for i in range(x - self._radius, x + self._radius + 1):
            for j in range(y - self._radius, y + self._radius + 1):
                if position.get_distance(i, j) > self._radius or position.get_distance(i, j) == 0:
                    # not area of attack position
                    continue
                new_position = Position(i, j)
                if map.is_valid_position(new_position):
                    map.interact_direct(new_position, self._force)
