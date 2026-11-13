from abc import ABC

from game import IActor
from positioning import ICellObject


class IEnemy(ABC, IActor, ICellObject):
    # Why is it here?
    pass
