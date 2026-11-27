from abc import ABC, abstractmethod

from positioning.cell_object_interface import ICellObject
from positioning.direction import Direction
from positioning.position import Position


class IMap(ABC):
    @abstractmethod
    def move(self, obj: ICellObject, direction: Direction) -> bool:
        """Attempt to move an object into a neighboring cell."""
        pass

    @abstractmethod
    def interact(self, obj: ICellObject, direction: Direction, force: int) -> bool:
        """Apply force to an object in a neighboring cell."""
        pass

    @abstractmethod
    def interact_direct(self, position: Position, force: int):
        """Apply force to an object at the specified position."""
        pass

    @abstractmethod
    def is_valid_position(self, position: Position | None) -> bool:
        """Check whether a position is within the map."""
        pass

    @abstractmethod
    def get_hero_position(self) -> Position:
        """Return the current position of the hero."""
        pass

    @abstractmethod
    def find_path_to_hero(self, position: Position | None) -> list[Direction]:
        """Return a sequence of directions leading to the hero."""
        pass

    @abstractmethod
    def replace_object(self, old: ICellObject, new: ICellObject) -> bool:
        """Replace an object in the cell it occupies."""
        pass
