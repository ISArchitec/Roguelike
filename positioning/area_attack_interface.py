from abc import ABC, abstractmethod

from positioning.map_interface import IMap
from positioning.position import Position


class IAreaAttack(ABC):
    # Probably should not be in positioning, but i dont know, where
    @abstractmethod
    def special_attack(self, map: IMap, position: Position):
        pass
