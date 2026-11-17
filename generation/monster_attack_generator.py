import random

from game import IAreaAttack


class MonsterAttackGenerator:
    def __init__(self, attack_pool: list[IAreaAttack]):
        self.attack_pool = attack_pool

    def generate_monster_attack(self) -> IAreaAttack:
        return random.choice(self.attack_pool)
