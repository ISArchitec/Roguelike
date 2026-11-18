from hero import IEvent
from hero.hero import Hero
from positioning import Direction


class MovingEvent(IEvent):
    def __init__(self, direction: Direction):
        self._direction = direction

    def accept_hero(self, hero: Hero) -> None:
        """Move or interact in the selected direction."""
        hero.set_action_succeeded(hero.try_move(self._direction))
