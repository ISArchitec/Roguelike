from abc import ABC, abstractmethod

from bonuses.id_card import IDCard
from bonuses.one_time_bonus import OneTimeBonus
from positioning.cell_object_interface import ICellObject
from positioning.direction import Direction
from positioning.position import Position


class IModelSubscriber(ABC):
    @abstractmethod
    def on_won(self) -> None:
        pass

    @abstractmethod
    def on_lost(self) -> None:
        pass

    @abstractmethod
    def draw_passage(self, p: Position) -> None:
        pass

    @abstractmethod
    def draw_object(self, p: ICellObject) -> None:
        pass

    @abstractmethod
    def register_move(self, p: Position, d: Direction) -> None:
        pass

    @abstractmethod
    def register_attack(self, p: Position, d: Direction) -> None:
        pass

    @abstractmethod
    def register_special_attack(self, p: Position, radius: int) -> None:
        pass

    @abstractmethod
    def show_things(self, ts: list[OneTimeBonus]) -> None:
        pass

    @abstractmethod
    def choose_from_cards(self, ics: list[IDCard]) -> int:
        pass
