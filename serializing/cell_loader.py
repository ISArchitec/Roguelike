from game import IActor
from map import Cell
from positioning import Position
from serializing.cell_object_loader import ICellObjectLoader
from serializing.position_loader import PositionLoader
from serializing.save_data import CellData


class CellLoader:
    """Convert map cells to and from save data."""

    @staticmethod
    def save_to(cell: Cell, actors: tuple[IActor, ...]) -> CellData:
        """Capture a cell and its actor reference or collectible."""
        obj = cell.get_object()
        index = next((index for index, actor in enumerate(actors) if actor is obj), None)
        data = CellData(cell.is_wall(), actor_index=index)
        if obj is not None and index is None:
            data.object = ICellObjectLoader.save_to(obj)
        return data

    @staticmethod
    def load_from(data: CellData, position: Position) -> Cell:
        """Restore a cell and its collectible at the supplied position."""
        if data.actor_index is not None and data.object is not None:
            raise ValueError("Invalid cell content")
        obj = None
        if data.object is not None:
            obj = ICellObjectLoader.load_from(data.object)
        if obj is not None:
            obj_position = obj.get_position()
            if obj_position is None or PositionLoader.save_to(obj_position) != PositionLoader.save_to(position):
                raise ValueError("Object position does not match its cell")
        return Cell.create_from(position, obj, data.wall)
