from positioning import ICellObject, Position


class Cell:
    def __init__(self, p: Position, object: ICellObject | None = None, is_wall: bool = False):
        if is_wall and object is not None:
            raise ValueError("A wall cannot contain an object")
        self._position = p
        self._object = object
        self._is_wall = is_wall

    @staticmethod
    def create_new(p: Position, is_wall: bool = False) -> "Cell":
        """Create an empty cell at the given position, optionally with a wall."""
        return Cell(p, is_wall=is_wall)

    @staticmethod
    def create_from(p: Position, object: ICellObject | None, is_wall: bool) -> "Cell":
        """Create a cell with the given occupant and wall state."""
        return Cell(p, object, is_wall)

    @property
    def position(self) -> Position:
        """Return the position of the cell."""
        return self._position

    def add_cell_object(self, o: ICellObject) -> bool:
        """Add an object if the cell is empty and report success."""
        if not self.empty():
            return False
        self._object = o
        return True

    def remove_cell_object(self, o: ICellObject) -> None:
        """Remove the object only if it occupies this cell."""
        if self._object is o:
            self._object = None

    def check_in(self, o: ICellObject) -> bool:
        """Check whether this exact object occupies the cell."""
        return o is self._object

    def get_object(self) -> ICellObject | None:
        """Return the occupant, or None if the cell is empty."""
        return self._object

    def make_wall(self) -> None:
        """Turn an empty cell into a wall."""
        if not self.empty():
            raise ValueError("An occupied cell cannot become a wall")
        self._is_wall = True

    def remove_wall(self) -> None:
        """Remove the wall from this cell."""
        if not self.is_wall():
            raise ValueError("Already no walls here")
        self._is_wall = False

    def is_wall(self) -> bool:
        """Check whether this cell is a wall."""
        return self._is_wall

    def empty(self) -> bool:
        """Check whether the cell has no occupant."""
        return self._object is None
