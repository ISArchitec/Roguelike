class ActorParams:
    def __init__(self, health: int, defence: int, attack: int, speed: int):
        self.health = health
        self.defence = defence
        self.attack = attack
        self.speed = speed

    def __add__(self, other):
        return ActorParams(self.health + other.health, self.defence + other.defence, self.attack + other.attack,
                           self.speed + other.speed)

    def get_hit(self, force: int):
        # Think about more difficult formula
        hit = max(force - self.defence, 0)
        return ActorParams(self.health - hit, self.defence, self.attack, self.speed)
