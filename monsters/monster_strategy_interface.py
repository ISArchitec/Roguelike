from abc import ABC, abstractmethod

from game import IAreaAttack
from monsters.monster_action import MonsterAction
from positioning import IMap, Position


class IMonsterStrategy(ABC):
    @abstractmethod
    def action(
        self,
        map: IMap,
        monster_position: Position,
        hero_position: Position,
        special_attack: IAreaAttack | None,
        speed: int,
    ) -> list[MonsterAction]:
        pass
