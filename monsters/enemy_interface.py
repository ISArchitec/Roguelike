from abc import abstractmethod

from game import ActorParams, IActor
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import ICellObject


class IEnemy(IActor, ICellObject):
    @abstractmethod
    def get_strategy(self) -> IMonsterStrategy:
        pass

    @abstractmethod
    def get_params(self) -> ActorParams:
        pass
