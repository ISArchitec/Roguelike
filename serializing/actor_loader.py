from queue import Queue

from bonuses import Certificate, IDCard
from game import IActor
from hero import Hero, IEvent
from monster_strategies.simple_monster_strategy import SimpleMonsterStrategy
from monsters import BossMonster, Monster
from positioning import IMap
from serializing.cell_object_loader import ICellObjectLoader
from serializing.one_time_bonus_loader import OneTimeBonusLoader
from serializing.position_loader import PositionLoader
from serializing.save_data import ActorData, ActorType, AttackData, InventoryData, ParamsData, StrategyType


class IActorLoader:
    """Convert heroes and enemies to and from save data."""

    @staticmethod
    def save_to(actor: IActor) -> ActorData:
        """Capture the state of a supported actor."""
        if type(actor) not in (Hero, Monster, BossMonster):
            raise ValueError(f"Unsupported actor type: {type(actor).__name__}")
        position = PositionLoader.save_to(actor.get_position())
        params = ParamsData.from_params(actor.get_params())
        if type(actor) is Hero:
            return ActorData(ActorType.HERO, params, position, inventory=IActorLoader._save_inventory(actor))
        if type(actor.get_strategy()) is not SimpleMonsterStrategy:
            raise ValueError(f"Unsupported monster strategy: {type(actor.get_strategy()).__name__}")
        if type(actor) is BossMonster:
            return ActorData(ActorType.BOSS, params, position, strategy=StrategyType.SIMPLE,
                             attack=AttackData.from_attack(actor.get_attack()))
        return ActorData(ActorType.MONSTER, params, position, strategy=StrategyType.SIMPLE)

    @staticmethod
    def load_from(data: ActorData, event_queue: Queue[IEvent], game_map: IMap | None = None) -> IActor:
        """Restore an actor, using a map when restoring an enemy."""
        params = data.params.to_params()
        position = PositionLoader.load_from(data.position)
        if data.type is ActorType.HERO:
            if data.inventory is None or data.strategy is not None or data.attack is not None:
                raise ValueError("Invalid hero data")
            return IActorLoader._load_hero(data.inventory, params, position, event_queue)
        if data.inventory is not None or data.strategy is not StrategyType.SIMPLE:
            raise ValueError("Invalid monster data")
        if game_map is None:
            raise ValueError("A map is required to restore an enemy")
        strategy = SimpleMonsterStrategy()
        if data.type is ActorType.MONSTER and data.attack is None:
            return Monster(params, position, game_map, strategy)
        if data.type is ActorType.BOSS and data.attack is not None:
            return BossMonster(params, position, game_map, strategy, data.attack.to_attack())
        raise ValueError("Invalid actor type or attack")

    @staticmethod
    def _save_inventory(hero: Hero) -> InventoryData:
        cards = list(hero.get_id_cards())
        selected = hero.get_current_id_card()
        selected_index = next((index for index, card in enumerate(cards) if card is selected), None)
        if selected is not None and selected_index is None:
            raise ValueError("Current card is not in the inventory")
        return InventoryData(
            [OneTimeBonusLoader.save_to(bonus) for bonus in hero.get_one_time_bonuses()],
            [ICellObjectLoader.save_to(card) for card in cards], selected_index,
            [ICellObjectLoader.save_to(item) for item in hero.get_certificates()])

    @staticmethod
    def _load_hero(data, params, position, event_queue):
        cards = [ICellObjectLoader.load_from(item) for item in data.id_cards]
        certificates = [ICellObjectLoader.load_from(item) for item in data.certificates]
        if any(type(card) is not IDCard for card in cards):
            raise ValueError("Invalid card in inventory")
        if any(type(item) is not Certificate for item in certificates):
            raise ValueError("Invalid certificate in inventory")
        index = data.current_id
        if index is not None and not 0 <= index < len(cards):
            raise ValueError("Invalid current card index")
        hero = Hero.construct_from(params, position, [OneTimeBonusLoader.load_from(item) for item in data.one_timers],
                                   cards, None if index is None else cards[index], certificates, event_queue)
        if hero.is_inactive():
            raise ValueError("Cannot load a game after the hero has died")
        return hero
