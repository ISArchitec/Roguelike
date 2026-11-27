from abc import ABC, abstractmethod


class IActor(ABC):
    @abstractmethod
    def step(self):
        """Perform one turn for this actor."""
        pass
