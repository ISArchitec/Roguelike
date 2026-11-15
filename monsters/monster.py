from positioning import Position, IMap
from game import ActorParams
from monster_strategy_interface import IMonsterStrategy
from enemy_interface import IEnemy


class Monster(IEnemy):
    def __init__(self, params: ActorParams, position: Position, map: IMap, strategy: IMonsterStrategy):
        self._params = params
        self._position = position
        self._map = map
        self._strategy = strategy

    def get_position(self):
        return self._position

    def interact(self, force: int):
        self._params = self._params.get_hit(force)
        if self._params.health < 0:
            # TODO handle death of a monster
            pass

    def is_inactive(self) -> bool:
        # I have no idea, what does this mean
        return True

    def step(self):
        action_list = self._strategy.action(self._map, self._position, self._map.get_hero_position(), None,
                                            self._params.speed)
        for action in action_list:
            if action.is_moving():
                # Should be always true for now
                self._map.move(self, action.get_direction())
