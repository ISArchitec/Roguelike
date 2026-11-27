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
        """Return the monster's current position."""
        return self._position

    def get_params(self) -> ActorParams:
        """Return the monster's current parameters."""
        return self._params

    def get_strategy(self) -> IMonsterStrategy:
        """Return the monster's action strategy."""
        return self._strategy

    def get_map(self) -> IMap:
        """Return the map containing the monster."""
        return self._map

    def set_map(self, map: IMap):
        """Set the map used for the monster's actions."""
        self._map = map

    def set_position(self, position: Position) -> None:
        """Set the monster's position."""
        self._position = position

    def interact(self, force: int) -> ICellObject:
        """Apply a hit and return the monster or a confusion wrapper."""
        health = self._params.health
        self._params = self._params.get_hit(force)
        if force > randint(health // 2, health):
            return ConfusingDecorator(self)
        return self

    def is_inactive(self) -> bool:
        """Return whether the monster's health is nonpositive."""
        return self._params.health <= 0

    def step(self):
        """Perform the monster's strategy actions: move or attack the hero."""
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
