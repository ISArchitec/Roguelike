from abc import ABC, abstractmethod


class IActor(ABC):
    @abstractmethod
    def step(self):
        pass
