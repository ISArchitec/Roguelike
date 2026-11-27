from abc import ABC, abstractmethod

from bonuses.id_card import IDCard
from bonuses.one_time_bonus import OneTimeBonus
from positioning.cell_object_interface import ICellObject
from positioning.direction import Direction
from positioning.position import Position


class IModelSubscriber(ABC):
    @abstractmethod
    def on_won(self) -> None:
        """Notify the subscriber of victory on the current level."""
        pass

    @abstractmethod
    def on_total_won(self) -> None:
        """Notify the subscriber of final victory in the game."""
        pass

    @abstractmethod
    def on_lost(self) -> None:
        """Notify the subscriber that the hero has lost."""
        pass

    @abstractmethod
    def draw_passage(self, p: Position) -> None:
        """Draw the map cell at position p."""
        pass

    @abstractmethod
    def draw_object(self, p: ICellObject) -> None:
        """Draw map object p."""
        pass

    @abstractmethod
    def register_move(self, p: Position, d: Direction) -> None:
        """Record movement from position p in direction d."""
        pass

    @abstractmethod
    def register_attack(self, p: Position, d: Direction) -> None:
        """Record a normal attack from position p in direction d."""
        pass

    @abstractmethod
    def register_special_attack(self, p: Position, radius: int) -> None:
        """Record a special attack centered at p with the given radius."""
        pass

    @abstractmethod
    def show_things(self, ts: list[OneTimeBonus]) -> None:
        """Show the available one-time bonuses in ts."""
        pass

    @abstractmethod
    def choose_from_cards(self, ics: list[IDCard]) -> int:
        """Choose an ID card and return its index in ics."""
        pass
