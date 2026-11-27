from game import ActorParams


class OneTimeBonus:
    def __init__(self, modifier: ActorParams):
        self._modifier = modifier

    def get_modifier(self):
        """Return this one-time bonus's stat modifiers."""
        return self._modifier
