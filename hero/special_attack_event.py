from hero import IEvent
from hero.hero import Hero


class SpecialAttackEvent(IEvent):
    def accept_hero(self, hero: Hero) -> None:
        """Use the equipped special attack when available."""
        hero.set_action_succeeded(hero.special_attack())
