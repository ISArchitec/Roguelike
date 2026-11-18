import random

from generation.level_generator_interface import ILevelGenerator
from generation.monster_params_generator import MonsterParamsGenerator
from generation.monster_strategy_generator import MonsterStrategyGenerator
from hero import Hero
from map import Map, MapBuilder
from monsters import IEnemy, Monster
from play_cycle import IModelSubscriber
from positioning import Position


class CommonLevelGenerator(ILevelGenerator):
    def __init__(
        self,
        width: int,
        height: int,
        hallway_width_range: tuple[int, int],
        corner_size_range: tuple[int, int],
        enemies_range: tuple[int, int],
        params_gen: MonsterParamsGenerator,
        strategy_gen: MonsterStrategyGenerator,
    ):
        from generation.boss_level_generator import BossLevelGenerator

        self.map_width = width
        self.map_height = height
        self.hallway_width_range = hallway_width_range
        self.corner_size_range = corner_size_range
        self.enemies_range = enemies_range
        self.params_gen = params_gen
        self.strategy_gen = strategy_gen
        self.boss_generator: BossLevelGenerator | None = None
        self.level_in_section = 0
        self.legacy_progress = False

    def generate_level(
        self, section_number: int, hero: Hero, console: IModelSubscriber
    ) -> tuple[Map, list[IEnemy], bool]:
        """Generate the next regular level or the section's boss level."""
        levels_per_section = 5
        if self.boss_generator is not None and self.level_in_section == levels_per_section - 1:
            level = self.boss_generator.generate_level(section_number, hero, console)
            self.level_in_section = 0
            return level
        hallway_width = random.randint(self.hallway_width_range[0], self.hallway_width_range[1])
        corner_size = random.randint(self.corner_size_range[0], self.corner_size_range[1])
        enemies_count = random.randint(self.enemies_range[0], self.enemies_range[1])

        # For now there will be only one type of map.
        # In the future, there can be randomly generated type of map
        # Simple 2 corners hallway with side corners
        corner_y = random.randint(self.map_height // 3, self.map_height // 3 * 2)
        map_builder = MapBuilder(self.map_width, self.map_height, fill_with_walls=True)
        map_builder.fill_rectangle(0, 0, hallway_width, corner_y, False)
        map_builder.fill_rectangle(
            hallway_width, corner_y - hallway_width, self.map_width, corner_y, False
        )
        map_builder.fill_rectangle(
            self.map_width - hallway_width, corner_y, self.map_width, self.map_height, False
        )

        # Side corners
        up_start_corner_x = random.randint(
            2 * corner_size, self.map_width - hallway_width - 2 * corner_size
        )
        down_start_corner_x = random.randint(
            hallway_width + 2 * corner_size, self.map_width - 2 * corner_size
        )

        map_builder.fill_rectangle(
            up_start_corner_x,
            corner_y,
            up_start_corner_x + corner_size,
            corner_y + corner_size,
            False,
        )
        map_builder.fill_rectangle(
            down_start_corner_x,
            corner_y - hallway_width - 1 - corner_size,
            down_start_corner_x + corner_size,
            corner_y - hallway_width - 1,
            False,
        )

        hero.set_position(Position(0, 0))
        map_builder.add_hero(hero)
        map = map_builder.to_map(console)

        enemies = []
        occupied_positions = {(0, 0)}
        for _ in range(enemies_count):
            x = 0
            y = 0
            while (x, y) in occupied_positions:
                x = random.randint(0, self.map_width - 1)
                y = random.randint(corner_y - hallway_width, corner_y - 1)
            enemy = Monster(
                self.params_gen.generate_monster_params(section_number),
                Position(x, y),
                map,
                self.strategy_gen.generate_monster_strategy(),
            )
            if not map.add_object(enemy):
                raise ValueError("Cannot place enemy on the map")
            enemies.append(enemy)
            occupied_positions.add((x, y))

        self.level_in_section = (self.level_in_section + 1) % levels_per_section
        return map, list(enemies), False
