from hero import IEvent
from hero.hero import Hero


class OneTimeBonusEvent(IEvent):
    def __init__(self, index: int):
        self._index = index

    def accept_hero(self, hero: Hero) -> None:
        """Apply the selected consumable."""
        hero.use_one_timer(self._index)
