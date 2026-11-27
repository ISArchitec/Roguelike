import random

from game import ActorParams


class MonsterParamsGenerator:
    def __init__(self, params_pool: list[ActorParams]):
        self.params_pool = params_pool

    def generate_monster_params(self, section_number: int) -> ActorParams:
        """Choose monster parameters at random and scale them for the section."""
        params = random.choice(self.params_pool)
        multiplier = max(1, section_number)
        return ActorParams(
            params.health * multiplier,
            params.defence * multiplier,
            params.attack * multiplier,
            params.speed,
        )
