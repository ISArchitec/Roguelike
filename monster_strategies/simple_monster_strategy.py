from monsters import IMonsterStrategy
from positioning import Position, IAreaAttack, IMap


class SimpleMonsterStrategy(IMonsterStrategy):
    def __init__(self):
        pass

    def action(self, map: IMap, monster_position: Position, hero_position: Position, special_attack: IAreaAttack | None,
               speed: int):
        path = map.find_path_to_hero(monster_position)
        if speed < len(path):
            return path[:speed]
        return path + [path[-1]] * (speed - len(path))
