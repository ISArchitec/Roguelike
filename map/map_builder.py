from collections.abc import Callable

from hero import Hero
from map.cell import Cell
from map.map import Map
from play_cycle import IModelSubscriber
from positioning import ICellObject, Position


class MapBuilder:
    def __init__(self, width: int, height: int):
        if width <= 0 or height <= 0:
            raise ValueError("Map dimensions must be positive")
        self._width = width
        self._height = height
        self._cells = [Cell.create_new(Position(x, y))
                       for y in range(height) for x in range(width)]
        self._hero: Hero | None = None

    @staticmethod
    def new(width: int, height: int) -> "MapBuilder":
        return MapBuilder(width, height)

    def add_passage(self, position: Position) -> None:
        index = self._position_index(position)
        if self._cells[index].is_wall():
            self._cells[index] = Cell.create_new(position)

    def add_object(self, obj: ICellObject) -> None:
        cell = self._cells[self._position_index(obj.get_position())]
        if cell.is_wall():
            raise ValueError("Object cannot be placed in a wall")
        if not cell.add_cell_object(obj):
            raise ValueError("Cell is already occupied")

    def add_hero(self, hero: Hero) -> None:
        if self._hero is not None:
            raise ValueError("Hero has already been added")
        self.add_object(hero)
        self._hero = hero

    def to_map(self, console: IModelSubscriber, on_terminate_object: Callable[[], None]) -> Map:
        if self._hero is None:
            raise ValueError("Hero must be added before building the map")
        return Map.create_from(self._width, self._height, self._cells, self._hero, console, on_terminate_object)

    def _position_index(self, position: Position) -> int:
        if (position is None or not 0 <= position.get_x() < self._width
                or not 0 <= position.get_y() < self._height):
            raise ValueError("Position is outside the map")
        return position.get_y() * self._width + position.get_x()
