from collections import deque
from collections.abc import Callable

from game import IActor
from hero import Hero
from map.cell import Cell
from play_cycle import IModelSubscriber
from positioning import Direction, ICellObject, IMap, Position


class Map(IMap):
    def __init__(
        self, width: int, height: int, cells: list[Cell], hero: Hero, console: IModelSubscriber
    ):
        if width <= 0 or height <= 0:
            raise ValueError("Map dimensions must be positive")
        if len(cells) != width * height:
            raise ValueError("Map must contain exactly width * height cells")
        self._width = width
        self._height = height
        self._cells = cells
        self._console = console
        self._on_terminate_object: Callable[[], None] | None = None
        self._on_replace_object: Callable[[IActor, IActor], None] | None = None
        self._hero = hero

    @staticmethod
    def create_from(
        width: int, height: int, cells: list[Cell], hero: Hero, console: IModelSubscriber
    ) -> "Map":
        """Create a map from its dimensions, cells, hero, and event subscriber."""
        return Map(width, height, cells, hero, console)

    def set_on_terminate_object(self, callback: Callable[[], None]) -> None:
        """Set the callback invoked when a defeated object is removed."""
        self._on_terminate_object = callback

    def set_on_replace_object(self, callback: Callable[[IActor, IActor], None]) -> None:
        """Set the callback invoked when one actor replaces another."""
        self._on_replace_object = callback

    def draw(self) -> None:
        """Send walls and map occupants to the event subscriber for rendering."""
        for cell in self._cells:
            if cell.is_wall():
                self._console.draw_passage(cell.position)
                continue
            if not cell.empty():
                obj = cell.get_object()
                if obj is not None:
                    self._console.draw_object(obj)

    def move(self, obj: ICellObject, direction: Direction) -> bool:
        """Move an object into a free neighboring cell and report success."""
        position = obj.get_position()
        if position is None:
            return False
        source = self._get_cell(position)
        if source is None or not source.check_in(obj):
            return False
        target_position = position.move(direction)
        target = self._get_cell(target_position)
        if target is None or target.is_wall() or not target.empty():
            return False
        obj.set_position(target_position)
        source.remove_cell_object(obj)
        target.add_cell_object(obj)
        self._console.register_move(position, direction)
        return True

    def interact(self, obj: ICellObject, direction: Direction, force: int) -> bool:
        """Attack an occupied neighboring cell on behalf of an object and report success."""
        position = obj.get_position()
        if position is None:
            return False
        source = self._get_cell(position)
        if source is None or not source.check_in(obj):
            return False
        target = self._get_cell(position.move(direction))
        if target is None or target.is_wall() or target.empty():
            return False
        self._console.register_attack(position, direction)
        self._hit_cell(target, force)
        return True

    def interact_direct(self, position: Position, force: int) -> None:
        """Apply a hit to the specified cell if it is accessible."""
        cell = self._get_cell(position)
        if cell is not None and not cell.is_wall():
            self._hit_cell(cell, force)

    def add_object(self, obj: ICellObject) -> bool:
        """Place an object in the free cell at its position and report success."""
        cell = self._get_cell(obj.get_position())
        if cell is None or cell.is_wall():
            return False
        return cell.add_cell_object(obj)

    def replace_object(self, old: ICellObject, new: ICellObject) -> bool:
        """Replace an object in its cell, notify about actor changes, and report success."""
        position = old.get_position()
        if position is None:
            return False
        cell = self._get_cell(position)
        if cell is None or not cell.check_in(old):
            return False
        cell.remove_cell_object(old)
        cell.add_cell_object(new)
        if (
            self._on_replace_object is not None
            and isinstance(old, IActor)
            and isinstance(new, IActor)
        ):
            self._on_replace_object(old, new)
        return True

    def is_valid_position(self, position: Position | None) -> bool:
        """Check whether a position lies within the map bounds."""
        return (
            position is not None
            and 0 <= position.get_x() < self._width
            and 0 <= position.get_y() < self._height
        )

    def get_hero(self) -> Hero:
        """Return the hero on this map."""
        return self._hero

    def get_width(self) -> int:
        """Return the map width in cells."""
        return self._width

    def get_height(self) -> int:
        """Return the map height in cells."""
        return self._height

    def get_cells(self) -> tuple[Cell, ...]:
        """Return the map cells as a tuple."""
        return tuple(self._cells)

    def get_hero_position(self) -> Position:
        """Return the current position of the hero."""
        return self.get_hero().get_position()

    def find_path_to_hero(self, position: Position | None) -> list[Direction]:
        """Find the shortest path to the hero around walls and occupied cells."""
        source = self._get_cell(position)
        if position is None or source is None or source.is_wall():
            return []
        start = self._position_index(position)
        goal = self._position_index(self.get_hero_position())
        frontier = deque([start])
        previous: dict[int, tuple[int, Direction] | None] = {start: None}
        while frontier:
            current = frontier.popleft()
            if current == goal:
                path = []
                while (step := previous[current]) is not None:
                    current, direction = step
                    path.append(direction)
                path.reverse()
                return path
            current_position = self._cells[current].position
            for direction in Direction:
                neighbor = self._get_cell(current_position.move(direction))
                if neighbor is None or neighbor.is_wall():
                    continue
                key = self._position_index(neighbor.position)
                if key in previous or (key != goal and not neighbor.empty()):
                    continue
                previous[key] = (current, direction)
                frontier.append(key)
        return []

    def _position_index(self, position: Position) -> int:
        return position.get_y() * self._width + position.get_x()

    def _get_cell(self, position: Position | None) -> Cell | None:
        if position is None or not self.is_valid_position(position):
            return None
        return self._cells[self._position_index(position)]

    def _hit_cell(self, cell: Cell, force: int) -> None:
        obj = cell.get_object()
        if obj is None:
            return
        if self._on_terminate_object is None:
            raise RuntimeError("Object termination callback has not been set")
        replaced_obj = obj.interact(force)
        if obj.is_inactive():
            cell.remove_cell_object(obj)
            if obj is not self._hero:
                self._on_terminate_object()
            return
        if replaced_obj is not obj:
            self.replace_object(obj, replaced_obj)
