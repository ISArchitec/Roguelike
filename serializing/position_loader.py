from positioning import Position
from serializing.save_data import PositionData


class PositionLoader:
    """Convert map positions to and from save data."""

    @staticmethod
    def save_to(position: Position) -> PositionData:
        """Capture a position."""
        return PositionData(position.get_x(), position.get_y())

    @staticmethod
    def load_from(data: PositionData) -> Position:
        """Restore a position."""
        if data.x < 0 or data.y < 0:
            raise ValueError("Invalid position")
        return Position(data.x, data.y)
