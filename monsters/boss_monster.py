from typing import cast

from game import ActorParams, IAreaAttack
from monsters.enemy_interface import IEnemy
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import Direction, IMap, Position


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
        return self._position

    def get_params(self) -> ActorParams:
        return self._params

    def get_strategy(self) -> IMonsterStrategy:
        return self._strategy

    def get_attack(self) -> IAreaAttack:
        return self._attack

    def set_map(self, map: IMap):
        self._map = map

    def set_position(self, position: Position) -> None:
        self._position = position

    def interact(self, force: int):
        self._params = self._params.get_hit(force)

    def is_inactive(self) -> bool:
        return self._params.health <= 0

    def step(self):
        action_list = self._strategy.action(
            self._map,
            self._position,
            self._map.get_hero_position(),
            self._attack,
            self._params.speed,
        )
        for action in action_list:
            if action.is_moving():
                self._map.move(self, cast(Direction, action.get_direction()))
            elif action.is_using_special_attack():
                self._attack.special_attack(self._map, self._position)
