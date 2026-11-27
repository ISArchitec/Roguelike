from positioning import Direction


class MonsterAction:
    def __init__(self, direction: Direction | None):
        self._direciton = direction

    def is_moving(self) -> bool:
        """Return whether this action specifies a movement direction."""
        return self._direciton is not None

    def is_using_special_attack(self) -> bool:
        """Return whether this action specifies a special attack without movement."""
        return self._direciton is None

    def get_direction(self) -> Direction | None:
        """Return the movement direction, or None for a special attack."""
        return self._direciton
