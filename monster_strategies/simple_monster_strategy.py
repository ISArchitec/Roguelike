from game import IAreaAttack
from monsters import IMonsterStrategy
from monsters.monster_action import MonsterAction
from positioning import IMap, Position


class SimpleMonsterStrategy(IMonsterStrategy):
    def __init__(self):
        pass

    def action(
        self,
        map: IMap,
        monster_position: Position,
        hero_position: Position,
        special_attack: IAreaAttack | None,
        speed: int,
    ) -> list[MonsterAction]:
        """Build movement actions toward the hero within the speed limit."""
        path = map.find_path_to_hero(monster_position)
        if len(path) == 0:
            return []
        directions = path[:speed] if speed < len(path) else path + [path[-1]] * (speed - len(path))
        return [MonsterAction(direction) for direction in directions]
