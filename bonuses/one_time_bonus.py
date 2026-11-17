from game import ActorParams


class OneTimeBonus:
    def __init__(self, modifier: ActorParams):
        self._modifier = modifier

    def get_modifier(self):
        return self._modifier
