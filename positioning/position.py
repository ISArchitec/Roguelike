from positioning.direction import Direction


# Position on the map. x is increasing from left to right, y is increasing from down to up
class Position:
    def __init__(self, x: int, y: int):
        self._x = x
        self._y = y

    def __eq__(self, other):
        return self._x == other.get_x() and self._y == other.get_y()

    def get_x(self):
        """Return the horizontal coordinate."""
        return self._x

    def get_y(self):
        """Return the vertical coordinate."""
        return self._y

    def move(self, direction: Direction):
        """Return a new position one step in the given direction."""
        match direction:
            case Direction.DOWN:
                return Position(self._x, self._y - 1)
            case Direction.UP:
                return Position(self._x, self._y + 1)
            case Direction.LEFT:
                return Position(self._x - 1, self._y)
            case Direction.RIGHT:
                return Position(self._x + 1, self._y)

    def get_distance(self, x: int, y: int):
        """Return the Manhattan distance to the given coordinates."""
        return abs(self._x - x) + abs(self._y - y)
