from abc import ABC, abstractmethod

from cell_object_interface import ICellObject
from direction import Direction
from position import Position


class IMap(ABC):
    @abstractmethod
    def move(self, obj: ICellObject, direction: Direction) -> bool:
        pass

    @abstractmethod
    def interact(self, obj: ICellObject, direction: Direction, force: int):
        pass

    @abstractmethod
    def interact_direct(self, position: Position, force: int):
        pass

    @abstractmethod
    def is_valid_position(self, position: Position):
        pass

    @abstractmethod
    def get_hero_position(self) -> Position:
        pass

    @abstractmethod
    def find_path_to_hero(self, position: Position) -> list[Direction]:
        pass
