from generation.level_generator_interface import ILevelGenerator
from generation.monster_attack_generator import MonsterAttackGenerator
from generation.monster_params_generator import MonsterParamsGenerator
from generation.monster_strategy_generator import MonsterStrategyGenerator
from hero import Hero
from map import Map, MapBuilder
from monsters import BossMonster, IEnemy
from play_cycle import IModelSubscriber
from positioning import Position


class BossLevelGenerator(ILevelGenerator):
    def __init__(
        self,
        width: int,
        height: int,
        hallway_width: int,
        params_gen: MonsterParamsGenerator,
        strategy_gen: MonsterStrategyGenerator,
        attack_gen: MonsterAttackGenerator,
    ):
        self.map_width = width
        self.map_height = height
        self.hallway_width = hallway_width
        self.params_gen = params_gen
        self.strategy_gen = strategy_gen
        self.attack_gen = attack_gen

    def generate_level(
        self, section_number: int, hero: Hero, console: IModelSubscriber
    ) -> tuple[Map, list[IEnemy], bool]:
        # For now there will be only one type of map.
        # In the future, there can be randomly generated type of map
        # Simple hallway from top to bottom
        map_builder = MapBuilder(self.map_width, self.map_height, fill_with_walls=True)
        map_builder.fill_rectangle(
            (self.map_width - self.hallway_width) // 2,
            0,
            (self.map_width + self.hallway_width) // 2,
            self.map_height - 1,
            False,
        )
        hero.set_position(Position(self.map_width // 2, 0))
        map_builder.add_hero(hero)
        map = map_builder.to_map(console)
        enemies = [
            BossMonster(
                self.params_gen.generate_monster_params(section_number),
                Position(self.map_width // 2, self.map_height - 1),
                map,
                self.strategy_gen.generate_monster_strategy(),
                self.attack_gen.generate_monster_attack(),
            )
        ]
        # I love pyright so i have to copy list for it to be correct type
        return map, list(enemies), True
