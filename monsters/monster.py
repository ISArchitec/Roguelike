from random import randint
from typing import cast

from game import ActorParams
from monsters.confusing_decorator import ConfusingDecorator
from monsters.enemy_interface import IEnemy
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import Direction, ICellObject, IMap, Position


class Monster(IEnemy):
    def __init__(
        self, params: ActorParams, position: Position, map: IMap, strategy: IMonsterStrategy
    ):
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

    def get_map(self) -> IMap:
        return self._map

    def set_map(self, map: IMap):
        self._map = map

    def set_position(self, position: Position) -> None:
        self._position = position

    def interact(self, force: int) -> ICellObject:
        health = self._params.health
        self._params = self._params.get_hit(force)
        if force > randint(health // 2, health):
            return ConfusingDecorator(self)
        return self

    def is_inactive(self) -> bool:
        return self._params.health <= 0

    def step(self):
        action_list = self._strategy.action(
            self._map, self._position, self._map.get_hero_position(), None, self._params.speed
        )
        for action in action_list:
            if action.is_moving():
                direction = cast(Direction, action.get_direction())
                if self._position.move(direction) == self._map.get_hero_position():
                    self._map.interact(self, direction, self._params.attack)
                else:
                    self._map.move(self, direction)
