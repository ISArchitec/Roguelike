from collections.abc import Iterator
from queue import Queue

from bonuses import Certificate, IDCard, OneTimeBonus
from game import ActorParams, IActor
from hero.event_interface import IEvent
from hero.inventory import Inventory
from positioning import Direction, ICellObject, IMap, Position


class Hero(IActor, ICellObject):
    def __init__(
        self,
        params: ActorParams,
        position: Position,
        one_timers: list[OneTimeBonus],
        event_queue: Queue[IEvent],
    ):
        self._params = params
        self._position = position
        self._one_timers = one_timers.copy()
        self._event_queue = event_queue
        self._map: IMap | None = None
        self._inventory = Inventory(self._one_timers, [], None, [])
        self._action_succeeded = True

    @classmethod
    def construct_from(
        cls,
        params: ActorParams,
        position: Position,
        one_timers: list[OneTimeBonus],
        id_cards: list[IDCard],
        current_id: IDCard | None,
        certificates: list[Certificate],
        event_queue: Queue[IEvent],
    ):
        """Restore a hero with the given parameters, inventory, and event queue."""
        hero = Hero(params, position, one_timers, event_queue)
        if current_id is not None:
            hero._inventory.use_id_card_direct(current_id)
        for card in id_cards:
            hero._inventory.add_id_card(card)
        for certificate in certificates:
            hero._inventory.add_certificate(certificate)
        return hero

    def set_map(self, map: IMap) -> None:
        """Set the map used for the hero's movement and attacks."""
        self._map = map

    def set_action_succeeded(self, succeeded: bool) -> None:
        """Record whether the current action consumed one of the hero's actions."""
        self._action_succeeded = succeeded

    # Cell object methods

    def get_position(self) -> Position:
        """Return the hero's current map position."""
        return self._position

    def get_params(self) -> ActorParams:
        """Return the hero's current health, defence, attack, and speed."""
        return self._params

    def get_certificates(self) -> Iterator[Certificate]:
        """Return an iterator over the hero's certificates."""
        return self._inventory.get_certificates()

    def set_position(self, position: Position) -> None:
        """Set the hero's position to position."""
        self._position = position

    def interact(self, force: int) -> ICellObject:
        """Apply a hit of force, update health, and return the hero."""
        self._params = self._params.get_hit(force)
        return self

    def is_inactive(self) -> bool:
        """Return whether the hero's health is nonpositive."""
        return self._params.health <= 0

    # Actor methods

    def step(self):
        """Process queued events until the hero uses all actions for this turn."""
        actions_left = self._params.speed
        while actions_left > 0:
            event = self._event_queue.get()
            self._action_succeeded = True
            event.accept_hero(self)
            if self._action_succeeded:
                actions_left -= 1

    # Inventory handling

    def get_one_time_bonuses(self):
        """Return an iterator over the hero's one-time bonuses."""
        return self._inventory.get_one_time_bonuses()

    def get_id_cards(self):
        """Return an iterator over the hero's ID cards."""
        return self._inventory.get_id_cards()

    def get_current_id_card(self) -> IDCard | None:
        """Return the selected ID card, or None if no card is selected."""
        return self._inventory.get_current_id_card()

    def chose_id_card(self) -> bool:
        """Return whether an ID card is selected for a special attack."""
        return self._inventory.chose_id_card()

    def reset_id_card(self):
        """Clear the selected ID card."""
        self._inventory.reset_id_card()

    def use_id_card(self, index: int):
        """Select the ID card at the given inventory index."""
        self._inventory.use_id_card(index)

    def add_id_card(self, id_card: IDCard):
        """Add an ID card to the hero's inventory."""
        self._inventory.add_id_card(id_card)

    def add_certificate(self, certificate: Certificate):
        """Apply a certificate to the hero and store it in the inventory."""
        self._params = certificate.apply(self._params)
        self._inventory.add_certificate(certificate)

    def use_one_timer(self, index: int):
        """Consume an item and apply its modifier to the hero."""
        bonus = list(self._inventory.get_one_time_bonuses())[index]
        self._inventory.use_one_timer(index)
        self._params = self._params + bonus.get_modifier()

    # Actions

    def try_move(self, direction: Direction) -> bool:
        """Move into an empty cell or interact with an occupied adjacent cell."""
        if self._map is None:
            raise RuntimeError("Hero map has not been set")
        if self._map.move(self, direction):
            return True
        return self._map.interact(self, direction, self._params.attack)

    def special_attack(self) -> bool:
        """Use the selected ID card and report whether its attack succeeded."""
        id_card = self._inventory.get_current_id_card()
        if id_card is None:
            return False
        if self._map is None:
            raise RuntimeError("Hero map has not been set")
        return id_card.special_attack(self._map, self._position)
