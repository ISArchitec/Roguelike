from abc import ABC, abstractmethod

from positioning.position import Position


class ICellObject(ABC):
    @abstractmethod
    def get_position(self) -> Position | None:
        """Return the object position, or None if it is not placed."""
        pass

    @abstractmethod
    def set_position(self, position: Position) -> None:
        """Set the object position on the map."""
        pass

    @abstractmethod
    def interact(self, force: int) -> "ICellObject":
        """Apply an interaction with the given force and return the cell object."""
        pass

    @abstractmethod
    def is_inactive(self) -> bool:
        """Check whether the object should be removed after interaction."""
        pass
