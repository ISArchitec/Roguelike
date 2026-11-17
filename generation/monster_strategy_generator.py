import random

from monsters import IMonsterStrategy


class MonsterStrategyGenerator:
    def __init__(self, strategies_pool: list[IMonsterStrategy]):
        self.strategies_pool = strategies_pool

    def generate_monster_strategy(self) -> IMonsterStrategy:
        return random.choice(self.strategies_pool)
