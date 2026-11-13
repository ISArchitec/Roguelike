from collections import deque

from game import ActorParams, IEvent, IActor
from positioning import Position, IMap, ICellObject, Direction
from bonuses import OneTimeBonus, IDCard, Certificate
from inventory import Inventory


class Hero(IActor, ICellObject):
    def __init__(self, params: ActorParams, position: Position, one_timers: list[OneTimeBonus],
                 event_queue: deque[IEvent], map: IMap):
        self._params = params
        self._position = position
        self._one_timers = one_timers.copy()
        self._event_queue = event_queue
        self._map = map
        self._inventory = Inventory(self._one_timers, [], None, [])

    @classmethod
    def construct_from(cls, params: ActorParams, position: Position, one_timers: list[OneTimeBonus],
                       id_cards: list[IDCard], current_id: IDCard | None, certificates: list[Certificate],
                       event_queue: deque[IEvent], map: IMap):
        hero = Hero(params, position, one_timers, event_queue, map)
        if current_id is not None:
            hero._inventory.use_id_card_direct(current_id)
        for card in id_cards:
            hero._inventory.add_id_card(card)
        for certificate in certificates:
            hero._inventory.add_certificate(certificate)
        return hero

    # Cell object methods

    def get_position(self) -> Position:
        return self._position

    def interact(self, force: int):
        self._params = self._params.get_hit(force)
        if self._params.health < 0:
            # TODO handle hero death
            pass

    def is_inactive(self) -> bool:
        # I have no idea, what does this mean
        return True

    # Actor methods

    def step(self):
        for i in range(self._params.speed):
            event = self._event_queue.popleft()
            event.accept_actor(self)

    # Inventory handling

    def get_one_time_bonuses(self):
        return self._inventory.get_one_time_bonuses()

    def get_id_cards(self):
        return self._inventory.get_id_cards()

    def get_current_id_card(self) -> IDCard | None:
        return self._inventory.get_current_id_card()

    def chose_id_card(self) -> bool:
        return self._inventory.chose_id_card()

    def reset_id_card(self):
        self._inventory.reset_id_card()

    def use_id_card(self, index: int):
        self._inventory.use_id_card(index)

    def add_id_card(self, id_card: IDCard):
        self._inventory.add_id_card(id_card)

    def add_certificate(self, certificate: Certificate):
        self._params = certificate.apply(self._params)
        self._inventory.add_certificate(certificate)

    def use_one_timer(self, index: int):
        self._inventory.use_one_timer(index)

    # Actions

    def try_move(self, direction: Direction) -> bool:
        return self._map.move(self, direction)

    def special_attack(self) -> bool:
        id_card = self._inventory.get_current_id_card()
        if id_card is None:
            return False
        id_card.special_attack(self._map, self._position)
        return True
