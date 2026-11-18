from abc import ABC, abstractmethod

from positioning.position import Position


class ICellObject(ABC):
    @abstractmethod
    def get_position(self) -> Position | None:
        pass

    @abstractmethod
    def set_position(self, position: Position) -> None:
        pass

    @abstractmethod
    def interact(self, force: int):
        pass

    @abstractmethod
    def is_inactive(self) -> bool:
        pass
