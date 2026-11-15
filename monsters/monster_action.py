from positioning import Direction


class MonsterAction:
    def __init__(self, direction: Direction | None):
        self._direciton = direction

    def is_moving(self) -> bool:
        return self._direciton is not None

    def is_using_special_attack(self) -> bool:
        return self._direciton is None

    def get_direction(self) -> Direction | None:
        return self._direciton
