from abc import ABC, abstractmethod

from actor_interface import IActor


class IEvent(ABC):
    @abstractmethod
    def accept_actor(self, actor: IActor):
        pass
