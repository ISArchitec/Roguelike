from abc import ABC, abstractmethod

import hero


class IEvent(ABC):
    @abstractmethod
    def accept_hero(self, hero: "hero.Hero") -> None:
        pass
