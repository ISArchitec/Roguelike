import json
import os
from hashlib import sha256
from datetime import datetime
from pathlib import Path
from queue import Queue
from tempfile import NamedTemporaryFile

from bonuses import Certificate, IDCard
from generation import ILevelGenerator
from hero import Hero, IEvent
from play_cycle import IModelSubscriber
from play_cycle.game import Game
from serializing.actor_loader import IActorLoader
from serializing.generator_loader import RandomLevelGeneratorLoader
from serializing.map_loader import MapLoader
from serializing.save_data import GameData, SaveDataCodec, SaveFileData


_SAVE_VERSION = 1
_HERO_INDEX = 0
_JSON_INDENT = 2


class GameLoader:
    """Save and restore game state at tick boundaries."""

    @staticmethod
    def save_to(game: Game) -> GameData:
        """Capture a game as typed save data."""
        if game.has_lost_level():
            raise ValueError("Cannot save a game after the hero has died")
        actors = game.get_actors()
        if not actors or actors[_HERO_INDEX] is not game.get_hero():
            raise ValueError("Invalid actor list")
        if len({id(actor) for actor in actors}) != len(actors):
            raise ValueError("Duplicate actor")
        return GameData(
            version=_SAVE_VERSION,
            generator=RandomLevelGeneratorLoader.save_to(game.get_level_generator()),
            section_passed=game.get_section_passed(),
            ticks=game.get_ticks(),
            enemy_count=game.get_enemy_count(),
            thing_got=game.get_thing_got(),
            is_section_end=game.get_is_section_end(),
            reward_placed=game.get_reward_placed(),
            save_date=game.get_save_date().isoformat(),
            actors=[IActorLoader.save_to(actor) for actor in actors],
            map=MapLoader.save_to(game.get_map(), actors),
        )

    @staticmethod
    def load_from(data: GameData, event_queue: Queue[IEvent], console: IModelSubscriber,
                  generator: ILevelGenerator) -> Game:
        """Restore a game using the supplied queue, subscriber and generator."""
        GameLoader._validate_game(data)
        generator = RandomLevelGeneratorLoader.load_from(data.generator, generator)
        if not data.actors:
            raise ValueError("Invalid hero in actor list")
        hero = IActorLoader.load_from(data.actors[_HERO_INDEX], event_queue)
        if type(hero) is not Hero:
            raise ValueError("Invalid hero in actor list")
        game_map = MapLoader.load_from(data.map, hero, console)
        hero.set_map(game_map)
        actors = [hero] + [IActorLoader.load_from(actor, event_queue, game_map) for actor in data.actors[1:]]
        if any(type(actor) is Hero for actor in actors[1:]):
            raise ValueError("Invalid hero in actor list")
        MapLoader.place_actors(data.map, game_map, actors)
        game = Game.create_from(data.section_passed, generator, game_map, actors[1:], data.ticks,
                                actors[_HERO_INDEX], console, data.enemy_count, data.thing_got,
                                data.is_section_end, data.reward_placed, datetime.fromisoformat(data.save_date))
        GameLoader._restore_rewards(game)
        return game

    @staticmethod
    def save_to_file(game: Game, path: str | Path) -> None:
        """Atomically write a game snapshot to a JSON file."""
        path = Path(path)
        snapshot = GameLoader.save_to(game)
        data = SaveDataCodec.to_dict(SaveFileData(snapshot, GameLoader._checksum(snapshot)))
        temporary_path = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
                temporary_path = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False, indent=_JSON_INDENT)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def load_from_file(path: str | Path, event_queue: Queue[IEvent], console: IModelSubscriber,
                       generator: ILevelGenerator) -> Game:
        """Read a JSON snapshot and restore the game."""
        with Path(path).open(encoding="utf-8") as stream:
            data = SaveDataCodec.file_from_dict(json.load(stream))
        if GameLoader._checksum(data.snapshot) != data.checksum:
            raise ValueError("Save checksum mismatch")
        return GameLoader.load_from(data.snapshot, event_queue, console, generator)

    @staticmethod
    def _checksum(snapshot: GameData) -> str:
        data = SaveDataCodec.to_dict(snapshot)
        serialized = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_game(data: GameData) -> None:
        if data.version != _SAVE_VERSION:
            raise ValueError("Unsupported save version")
        if min(data.section_passed, data.ticks, data.enemy_count, data.thing_got) < 0:
            raise ValueError("Invalid game counters")

    @staticmethod
    def _restore_rewards(game: Game) -> None:
        hero = game.get_hero()
        for cell in game.get_map().get_cells():
            reward = cell.get_object()
            if type(reward) is IDCard:
                reward.set_tick_getter(game.get_ticks)
                reward.set_on_pickup(lambda reward=reward: hero.add_id_card(reward))
            elif type(reward) is Certificate:
                reward.set_on_pickup(lambda reward=reward: hero.add_certificate(reward))
