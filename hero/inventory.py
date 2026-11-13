from bonuses import IDCard, Certificate, OneTimeBonus


class Inventory:
    def __init__(self, one_timers: list[OneTimeBonus], id_cards: list[IDCard], current_id: IDCard | None,
                 certificates: list[Certificate]):
        self._one_timers = one_timers.copy()
        self._id_cards = id_cards.copy()
        self._current_id = current_id
        self._certificates = certificates.copy()

    def get_one_time_bonuses(self):
        return iter(self._one_timers)

    def get_id_cards(self):
        return iter(self._id_cards)

    def get_current_id_card(self) -> IDCard | None:
        return self._current_id

    def chose_id_card(self):
        return self._current_id is not None

    def reset_id_card(self):
        self._current_id = None

    def use_id_card(self, index: int):
        self._current_id = self._id_cards[index]

    def use_id_card_direct(self, card: IDCard | None):
        # Should be used with caution, e.g. in loading game
        self._current_id = card

    def add_id_card(self, id_card: IDCard):
        self._id_cards.append(id_card)

    def add_certificate(self, certificate: Certificate):
        self._certificates.append(certificate)

    def use_one_timer(self, index: int):
        self._one_timers.pop(index)
