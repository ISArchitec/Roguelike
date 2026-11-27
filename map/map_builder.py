from hero import Hero
from map.cell import Cell
from map.map import Map
from play_cycle import IModelSubscriber
from positioning import ICellObject, Position


class MapBuilder:
    def __init__(self, width: int, height: int, fill_with_walls: bool = False):
        if width <= 0 or height <= 0:
            raise ValueError("Map dimensions must be positive")
        self._width = width
        self._height = height
        self._cells = [
            Cell.create_new(Position(x, y), is_wall=fill_with_walls)
            for y in range(height)
            for x in range(width)
        ]
        self._hero: Hero | None = None

    @staticmethod
    def new(width: int, height: int) -> "MapBuilder":
        """Create a wall-free map builder with the given dimensions."""
        return MapBuilder(width, height)

    def add_wall(self, position: Position) -> None:
        """Place a wall in the specified empty cell."""
        index = self._position_index(position)
        if self._cells[index].is_wall():
            raise ValueError("Wall cannot be placed in a wall")
        self._cells[index].make_wall()

    def remove_wall(self, position: Position) -> None:
        """Remove the wall from the specified cell."""
        index = self._position_index(position)
        if not self._cells[index].is_wall():
            raise ValueError("There is no wall")
        self._cells[index].remove_wall()

    def add_object(self, obj: ICellObject) -> None:
        """Place an object in a free cell of the map being built."""
        cell = self._cells[self._position_index(obj.get_position())]
        if cell.is_wall():
            raise ValueError("Object cannot be placed in a wall")
        if not cell.add_cell_object(obj):
            raise ValueError("Cell is already occupied")

    def add_hero(self, hero: Hero) -> None:
        """Place the single hero on the map being built."""
        if self._hero is not None:
            raise ValueError("Hero has already been added")
        self.add_object(hero)
        self._hero = hero

    def to_map(self, console: IModelSubscriber) -> Map:
        """Build a map with its hero and event subscriber."""
        if self._hero is None:
            raise ValueError("Hero must be added before building the map")
        return Map.create_from(self._width, self._height, self._cells, self._hero, console)

    def fill_rectangle(self, x0: int, y0: int, x1: int, y1: int, is_wall: bool):
        """Add or remove walls in a half-open rectangle."""
        for x in range(x0, x1):
            for y in range(y0, y1):
                if is_wall:
                    self.add_wall(Position(x, y))
                else:
                    self.remove_wall(Position(x, y))

    def _position_index(self, position: Position | None) -> int:
        if (
            position is None
            or not 0 <= position.get_x() < self._width
            or not 0 <= position.get_y() < self._height
        ):
            raise ValueError("Position is outside the map")
        return position.get_y() * self._width + position.get_x()
