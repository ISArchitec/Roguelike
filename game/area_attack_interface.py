from abc import ABC, abstractmethod

from positioning.map_interface import IMap
from positioning.position import Position


class IAreaAttack(ABC):
    @abstractmethod
    def special_attack(self, map: IMap, position: Position):
        """Apply this special attack to the map from position."""
        pass
