from abc import ABC, abstractmethod

from hero import Hero
from map import Map


class ILevelGenerator(ABC):
    @abstractmethod
    def generate_level(self, section_number: int, hero: Hero) -> Map:
        pass
