from abc import ABC, abstractmethod

from hero import Hero
from map import Map
from monsters import IEnemy
from play_cycle import IModelSubscriber


class ILevelGenerator(ABC):
    @abstractmethod
    def generate_level(
        self, section_number: int, hero: Hero, console: IModelSubscriber
    ) -> tuple[Map, list[IEnemy], bool]:
        # Последний элемент результата указывает, завершает ли созданный уровень секцию.
        pass
