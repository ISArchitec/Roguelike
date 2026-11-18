from typing import cast

from generation import (
    BossLevelGenerator,
    CommonLevelGenerator,
    ILevelGenerator,
    MonsterAttackGenerator,
    MonsterParamsGenerator,
    MonsterStrategyGenerator,
)
from monster_strategies.simple_monster_strategy import SimpleMonsterStrategy
from monsters import IMonsterStrategy
from serializing.save_data import (
    AttackData,
    GeneratorData,
    LevelGeneratorType,
    ParamsData,
    RangeData,
    StrategyType,
)


class RandomLevelGeneratorLoader:
    """Save and restore the configuration of supported level generators."""

    @staticmethod
    def save_to(generator: ILevelGenerator) -> GeneratorData:
        """Capture the concrete generator and its configuration."""
        if type(generator) not in (CommonLevelGenerator, BossLevelGenerator):
            raise ValueError(f"Unsupported level generator: {type(generator).__name__}")
        generator = cast(CommonLevelGenerator | BossLevelGenerator, generator)

        params = [ParamsData.from_params(item) for item in generator.params_gen.params_pool]
        strategies = [
            RandomLevelGeneratorLoader._save_strategy(item)
            for item in generator.strategy_gen.strategies_pool
        ]
        if isinstance(generator, CommonLevelGenerator):
            result = GeneratorData(
                type=LevelGeneratorType.COMMON,
                width=generator.map_width,
                height=generator.map_height,
                params_pool=params,
                strategies_pool=strategies,
                hallway_width_range=RangeData(*generator.hallway_width_range),
                corner_size_range=RangeData(*generator.corner_size_range),
                enemies_range=RangeData(*generator.enemies_range),
            )
            if generator.boss_generator is not None:
                vars(result)["level_in_section"] = generator.level_in_section
                vars(result)["boss"] = RandomLevelGeneratorLoader.save_to(generator.boss_generator)
            return result
        return GeneratorData(
            type=LevelGeneratorType.BOSS,
            width=generator.map_width,
            height=generator.map_height,
            params_pool=params,
            strategies_pool=strategies,
            hallway_width=generator.hallway_width,
            attacks_pool=[
                AttackData.from_attack(item) for item in generator.attack_gen.attack_pool
            ],
        )

    @staticmethod
    def load_from(data: GeneratorData) -> ILevelGenerator:
        """Recreate a supported generator from its saved configuration."""
        from play_cycle import GlobalConfig

        params_gen = MonsterParamsGenerator([item.to_params() for item in data.params_pool])
        strategy_gen = MonsterStrategyGenerator(
            [RandomLevelGeneratorLoader._load_strategy(item) for item in data.strategies_pool]
        )
        if data.type is LevelGeneratorType.COMMON:
            if (
                data.hallway_width_range is None
                or data.corner_size_range is None
                or data.enemies_range is None
                or data.hallway_width is not None
                or data.attacks_pool is not None
            ):
                raise ValueError("Invalid common level generator data")
            saved_boss = getattr(data, "boss", None)
            saved_level = getattr(data, "level_in_section", None)
            if saved_boss is None:
                if saved_level is not None:
                    raise ValueError("Invalid level in section")
                config = GlobalConfig.get_instance()
                boss_generator = BossLevelGenerator(
                    data.width,
                    data.height,
                    data.hallway_width_range.minimum,
                    MonsterParamsGenerator(config.get_boss_param_pool()),
                    MonsterStrategyGenerator([SimpleMonsterStrategy()]),
                    MonsterAttackGenerator(
                        [
                            config.get_boss_prizes(index).get_attack()
                            for index in range(config.get_boss_prize_pool_size())
                        ]
                    ),
                )
                level_in_section = 1
            else:
                if saved_level is None or not 0 <= saved_level < 5:
                    raise ValueError("Missing level in section")
                restored_boss = RandomLevelGeneratorLoader.load_from(saved_boss)
                if not isinstance(restored_boss, BossLevelGenerator):
                    raise ValueError("Invalid boss generator data")
                boss_generator = restored_boss
                level_in_section = saved_level
            generator = CommonLevelGenerator(
                data.width,
                data.height,
                (data.hallway_width_range.minimum, data.hallway_width_range.maximum),
                (data.corner_size_range.minimum, data.corner_size_range.maximum),
                (data.enemies_range.minimum, data.enemies_range.maximum),
                params_gen,
                strategy_gen,
            )
            generator.boss_generator = boss_generator
            generator.level_in_section = level_in_section
            generator.legacy_progress = saved_boss is None
            return generator
        if data.type is LevelGeneratorType.BOSS:
            if (
                data.hallway_width is None
                or data.attacks_pool is None
                or data.hallway_width_range is not None
                or data.corner_size_range is not None
                or data.enemies_range is not None
            ):
                raise ValueError("Invalid boss level generator data")
            return BossLevelGenerator(
                data.width,
                data.height,
                data.hallway_width,
                params_gen,
                strategy_gen,
                MonsterAttackGenerator([item.to_attack() for item in data.attacks_pool]),
            )
        raise ValueError(f"Unsupported level generator: {data.type!r}")

    @staticmethod
    def _save_strategy(strategy: IMonsterStrategy) -> StrategyType:
        if type(strategy) is SimpleMonsterStrategy:
            return StrategyType.SIMPLE
        raise ValueError(f"Unsupported monster strategy: {type(strategy).__name__}")

    @staticmethod
    def _load_strategy(strategy: StrategyType) -> IMonsterStrategy:
        if strategy is StrategyType.SIMPLE:
            return SimpleMonsterStrategy()
        raise ValueError(f"Unsupported monster strategy: {strategy!r}")
