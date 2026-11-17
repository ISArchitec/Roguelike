from typing import cast

from game import IActor
from hero import Hero
from map import Map
from play_cycle import IModelSubscriber
from positioning import ICellObject, Position
from serializing.cell_loader import CellLoader
from serializing.save_data import MapData


class MapLoader:
    """Convert maps to and from save data."""

    @staticmethod
    def save_to(game_map: Map, actors: tuple[IActor, ...]) -> MapData:
        """Capture the map with references to its actors."""
        width = game_map.get_width()
        cells = game_map.get_cells()
        for index, cell in enumerate(cells):
            if (cell.position.get_x(), cell.position.get_y()) != (index % width, index // width):
                raise ValueError("Invalid cell position")
        return MapData(
            width, game_map.get_height(), [CellLoader.save_to(cell, actors) for cell in cells]
        )

    @staticmethod
    def load_from(data: MapData, hero: Hero, console: IModelSubscriber) -> Map:
        """Restore the map before constructing its enemies."""
        if data.width <= 0 or data.height <= 0 or len(data.cells) != data.width * data.height:
            raise ValueError("Invalid map dimensions")
        cells = [
            CellLoader.load_from(cell, Position(index % data.width, index // data.width))
            for index, cell in enumerate(data.cells)
        ]
        return Map.create_from(data.width, data.height, cells, hero, console)

    @staticmethod
    def place_actors(data: MapData, game_map: Map, actors: list[IActor]) -> None:
        """Place restored actors in their saved cells."""
        if not actors or type(actors[0]) is not Hero:
            raise ValueError("Hero is missing from actor list")
        seen = set()
        for index, cell_data in enumerate(data.cells):
            if cell_data.actor_index is not None:
                actor_index = cell_data.actor_index
                if not 0 <= actor_index < len(actors) or actor_index in seen:
                    raise ValueError("Invalid actor reference")
                actor = cast(ICellObject, actors[actor_index])
                position = cast(Position, actor.get_position())
                if (position.get_x(), position.get_y()) != (
                    index % data.width,
                    index // data.width,
                ):
                    raise ValueError("Actor position does not match its cell")
                if not game_map.add_object(actor):
                    raise ValueError("Cannot place actor on the map")
                seen.add(actor_index)
        if 0 not in seen:
            raise ValueError("Hero is missing from the map")
