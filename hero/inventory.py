from collections.abc import Iterator

from bonuses import Certificate, IDCard, OneTimeBonus


class Inventory:
    def __init__(
        self,
        one_timers: list[OneTimeBonus],
        id_cards: list[IDCard],
        current_id: IDCard | None,
        certificates: list[Certificate],
    ):
        self._one_timers = one_timers.copy()
        self._id_cards = id_cards.copy()
        self._current_id = current_id
        self._certificates = certificates.copy()

    def get_one_time_bonuses(self):
        """Return an iterator over the inventory's one-time bonuses."""
        return iter(self._one_timers)

    def get_id_cards(self):
        """Return an iterator over the inventory's ID cards."""
        return iter(self._id_cards)

    def get_certificates(self) -> Iterator[Certificate]:
        """Return an iterator over the inventory's certificates."""
        return iter(self._certificates)

    def get_current_id_card(self) -> IDCard | None:
        """Return the selected ID card, or None if none is selected."""
        return self._current_id

    def chose_id_card(self):
        """Return whether an ID card is selected."""
        return self._current_id is not None

    def reset_id_card(self):
        """Clear the selected ID card."""
        self._current_id = None

    def use_id_card(self, index: int):
        """Select the ID card at the given index."""
        self._current_id = self._id_cards[index]

    def use_id_card_direct(self, card: IDCard | None):
        # Should be used with caution, e.g. in loading game
        """Set the selected ID card directly while restoring state."""
        self._current_id = card

    def add_id_card(self, id_card: IDCard):
        """Add an ID card to the inventory."""
        self._id_cards.append(id_card)

    def add_certificate(self, certificate: Certificate):
        """Add a certificate to the inventory."""
        self._certificates.append(certificate)

    def use_one_timer(self, index: int):
        """Remove the used one-time bonus at the given index."""
        self._one_timers.pop(index)
