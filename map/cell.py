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
        return Cell(p, is_wall=is_wall)

    @staticmethod
    def create_from(p: Position, object: ICellObject | None, is_wall: bool) -> "Cell":
        return Cell(p, object, is_wall)

    @property
    def position(self) -> Position:
        return self._position

    def add_cell_object(self, o: ICellObject) -> bool:
        if not self.empty():
            return False
        self._object = o
        return True

    def remove_cell_object(self, o: ICellObject) -> None:
        if self._object is o:
            self._object = None

    def check_in(self, o: ICellObject) -> bool:
        return o is self._object

    def get_object(self) -> ICellObject | None:
        return self._object

    def make_wall(self) -> None:
        if not self.empty():
            raise ValueError("An occupied cell cannot become a wall")
        self._is_wall = True

    def remove_wall(self) -> None:
        if not self.is_wall():
            raise ValueError("Already no walls here")
        self._is_wall = False

    def is_wall(self) -> bool:
        return self._is_wall

    def empty(self) -> bool:
        return self._object is None
