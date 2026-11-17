from positioning import Position, IMap
from game import ActorParams
from monsters.monster_strategy_interface import IMonsterStrategy
from monsters.enemy_interface import IEnemy


class Monster(IEnemy):
    def __init__(self, params: ActorParams, position: Position, map: IMap, strategy: IMonsterStrategy):
        self._params = params
        self._position = position
        self._map = map
        self._strategy = strategy

    def get_position(self):
        return self._position

    def get_params(self) -> ActorParams:
        return self._params

    def get_strategy(self) -> IMonsterStrategy:
        return self._strategy

    def set_map(self, map: IMap):
        self._map = map

    def set_position(self, position: Position) -> None:
        self._position = position

    def interact(self, force: int):
        self._params = self._params.get_hit(force)

    def is_inactive(self) -> bool:
        return self._params.health <= 0

    def step(self):
        action_list = self._strategy.action(self._map, self._position, self._map.get_hero_position(), None,
                                            self._params.speed)
        for action in action_list:
            if action.is_moving():
                # Should be always true for now
                self._map.move(self, action.get_direction())
