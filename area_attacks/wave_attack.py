from positioning import IAreaAttack, IMap, Position, Direction


class WaveAttack(IAreaAttack):
    def __init__(self, forces: list[int]):
        self._forces = forces.copy()

    def special_attack(self, map: IMap, position: Position):
        x = position.get_x()
        y = position.get_y()
        radius = len(self._forces)
        for i in range(x - radius, x + radius + 1):
            for j in range(y - radius, y + radius + 1):
                distance = position.get_distance(i, j)
                if distance > radius or distance == 0:
                    # not area of attack position
                    continue
                new_position = Position(i, j)
                if map.is_valid_position(new_position):
                    map.interact_direct(new_position, self._forces[distance - 1])
