from hero import IEvent
from hero.hero import Hero


class SpecialAttackEvent(IEvent):
    def accept_hero(self, hero: Hero) -> None:
        hero.special_attack()
