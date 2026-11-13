from abc import ABC, abstractmethod

from position import Position


class ICellObject(ABC):
    @abstractmethod
    def get_position(self) -> Position:
        pass

    @abstractmethod
    def interact(self, force: int):
        pass

    @abstractmethod
    def is_inactive(self) -> bool:
        pass
