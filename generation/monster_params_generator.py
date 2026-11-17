import random

from game import ActorParams


class MonsterParamsGenerator:
    def __init__(self, params_pool: list[ActorParams]):
        self.params_pool = params_pool

    def generate_monster_params(self, section_number: int) -> ActorParams:
        params = random.choice(self.params_pool)
        return ActorParams(
            params.health * section_number,
            params.defence * section_number,
            params.attack * section_number,
            params.speed,
        )
