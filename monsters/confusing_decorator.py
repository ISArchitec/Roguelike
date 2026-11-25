import random

from game import ActorParams
from monsters.enemy_interface import IEnemy
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import Direction, ICellObject, IMap, Position


class ConfusingDecorator(IEnemy):
    def __init__(self, enemy: IEnemy):
        self._enemy = enemy
        self._remain_confusing = 3

    def unwrap(self) -> IEnemy:
        return self._enemy

    def get_position(self) -> Position | None:
        return self._enemy.get_position()

    def set_position(self, position: Position) -> None:
        self._enemy.set_position(position)

    def interact(self, force: int) -> ICellObject:
        replaced_obj = self._enemy.interact(force)
        if replaced_obj != self._enemy:
            return replaced_obj
        return self

    def is_inactive(self) -> bool:
        return self._enemy.is_inactive()

    def get_strategy(self) -> IMonsterStrategy:
        return self._enemy.get_strategy()

    def get_params(self) -> ActorParams:
        return self._enemy.get_params()

    def get_map(self) -> IMap:
        return self._enemy.get_map()

    def step(self):
        for _ in range(self._enemy.get_params().speed):
            direction = random.choice(list(Direction))
            self.get_map().move(self._enemy, direction)
        self._remain_confusing -= 1
        if self._remain_confusing == 0:
            self.get_map().replace_object(self, self._enemy)
