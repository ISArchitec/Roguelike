import random

from game import ActorParams
from monsters.enemy_interface import IEnemy
from monsters.monster_strategy_interface import IMonsterStrategy
from positioning import Direction, ICellObject, IMap, Position


class ConfusingDecorator(IEnemy):
    def __init__(self, enemy: IEnemy, remaining_turns: int = 3):
        if remaining_turns <= 0:
            raise ValueError("Remaining confusion turns must be positive")
        self._enemy = enemy
        self._remain_confusing = remaining_turns

    def unwrap(self) -> IEnemy:
        """Return the monster temporarily wrapped by confusion."""
        return self._enemy

    def get_remaining_turns(self) -> int:
        """Return the number of confusion turns remaining."""
        return self._remain_confusing

    def get_position(self) -> Position | None:
        """Return the wrapped monster's position."""
        return self._enemy.get_position()

    def set_position(self, position: Position) -> None:
        """Set the wrapped monster's position."""
        self._enemy.set_position(position)

    def interact(self, force: int) -> ICellObject:
        """Pass a hit to the monster and return this or its new wrapper."""
        replaced_obj = self._enemy.interact(force)
        if replaced_obj != self._enemy:
            return replaced_obj
        return self

    def is_inactive(self) -> bool:
        """Return whether the wrapped monster is inactive."""
        return self._enemy.is_inactive()

    def get_strategy(self) -> IMonsterStrategy:
        """Return the wrapped monster's strategy."""
        return self._enemy.get_strategy()

    def get_params(self) -> ActorParams:
        """Return the wrapped monster's current parameters."""
        return self._enemy.get_params()

    def get_map(self) -> IMap:
        """Return the wrapped monster's map."""
        return self._enemy.get_map()

    def step(self):
        """Attempt random moves and remove confusion after the final turn."""
        for _ in range(self._enemy.get_params().speed):
            direction = random.choice(list(Direction))
            self.get_map().move(self, direction)
        self._remain_confusing -= 1
        if self._remain_confusing == 0:
            self.get_map().replace_object(self, self._enemy)
