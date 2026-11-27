from abc import abstractmethod

from game import ActorParams, IActor
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import ICellObject
from positioning.map_interface import IMap


class IEnemy(IActor, ICellObject):
    @abstractmethod
    def get_strategy(self) -> IMonsterStrategy:
        """Return the enemy's action selection strategy."""
        pass

    @abstractmethod
    def get_params(self) -> ActorParams:
        """Return the enemy's current combat parameters."""
        pass

    @abstractmethod
    def get_map(self) -> IMap:
        """Return the map on which the enemy acts."""
        pass
