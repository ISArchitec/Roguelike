from typing import cast

from game import ActorParams, IAreaAttack
from monsters.enemy_interface import IEnemy
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import Direction, ICellObject, IMap, Position


class BossMonster(IEnemy):
    def __init__(
        self,
        params: ActorParams,
        position: Position,
        map: IMap,
        strategy: IMonsterStrategy,
        attack: IAreaAttack,
    ):
        self._params = params
        self._position = position
        self._map = map
        self._strategy = strategy
        self._attack = attack

    def get_position(self):
        """Return the boss's current position."""
        return self._position

    def get_params(self) -> ActorParams:
        """Return the boss's current parameters."""
        return self._params

    def get_strategy(self) -> IMonsterStrategy:
        """Return the boss's action strategy."""
        return self._strategy

    def get_map(self) -> IMap:
        """Return the map containing the boss."""
        return self._map

    def get_attack(self) -> IAreaAttack:
        """Return the boss's special attack."""
        return self._attack

    def set_map(self, map: IMap):
        """Set the map used for the boss's actions."""
        self._map = map

    def set_position(self, position: Position) -> None:
        """Set the boss's position."""
        self._position = position

    def interact(self, force: int) -> ICellObject:
        """Apply a hit of force and return the boss."""
        self._params = self._params.get_hit(force)
        return self

    def is_inactive(self) -> bool:
        """Return whether the boss's health is nonpositive."""
        return self._params.health <= 0

    def step(self):
        """Perform the boss's strategy actions, including movement and special attacks."""
        action_list = self._strategy.action(
            self._map,
            self._position,
            self._map.get_hero_position(),
            self._attack,
            self._params.speed,
        )
        for action in action_list:
            if action.is_moving():
                direction = cast(Direction, action.get_direction())
                if self._position.move(direction) == self._map.get_hero_position():
                    self._map.interact(self, direction, self._params.attack)
                else:
                    self._map.move(self, direction)
            elif action.is_using_special_attack():
                self._attack.special_attack(self._map, self._position)
