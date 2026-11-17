from abc import ABC, abstractmethod

from hero import Hero
from map import Map
from monsters import IEnemy


class ILevelGenerator(ABC):
    @abstractmethod
    def generate_level(self, section_number: int, hero: Hero) -> tuple[Map, list[IEnemy], bool]:
        # Последний элемент результата указывает, завершает ли созданный уровень секцию.
        pass
