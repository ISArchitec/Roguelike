from game import IAreaAttack
from abc import ABC, abstractmethod

from monsters.monster_action import MonsterAction
from positioning import Position, IMap


class IMonsterStrategy(ABC):
    @abstractmethod
    def action(self, map: IMap, monster_position: Position, hero_position: Position, special_attack: IAreaAttack | None,
               speed: int) -> list[MonsterAction]:
        pass
