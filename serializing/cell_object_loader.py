from bonuses import Certificate, IDCard
from positioning import ICellObject
from serializing.position_loader import PositionLoader
from serializing.save_data import AttackData, ObjectData, ObjectType, ParamsData


class ICellObjectLoader:
    """Convert collectible map objects to and from save data."""

    @staticmethod
    def save_to(obj: ICellObject) -> ObjectData:
        """Capture a supported collectible object."""
        position = obj.get_position()
        position_data = PositionLoader.save_to(position) if position is not None else None
        if type(obj) is Certificate:
            return ObjectData(
                ObjectType.CERTIFICATE,
                position_data,
                params=ParamsData.from_params(obj.get_params()),
            )
        if type(obj) is IDCard:
            return ObjectData(
                ObjectType.ID_CARD,
                position_data,
                attack=AttackData.from_attack(obj.get_attack()),
                timeout=obj.get_timeout(),
                tick_since=obj.get_tick_since(),
            )
        raise ValueError(f"Unsupported object type: {type(obj).__name__}")

    @staticmethod
    def load_from(data: ObjectData) -> ICellObject:
        """Restore a collectible without runtime callbacks."""
        position = PositionLoader.load_from(data.position) if data.position is not None else None
        if data.type is ObjectType.CERTIFICATE:
            if data.params is None or any(
                value is not None for value in (data.attack, data.timeout, data.tick_since)
            ):
                raise ValueError("Invalid certificate data")
            certificate = Certificate(data.params.to_params())
            if position is not None:
                certificate.set_position(position)
            return certificate
        if data.type is ObjectType.ID_CARD:
            if (
                data.params is not None
                or data.attack is None
                or data.timeout is None
                or data.tick_since is None
            ):
                raise ValueError("Invalid card data")
            if data.timeout < 0 or data.tick_since < 0:
                raise ValueError("Invalid card cooldown")
            return IDCard(data.attack.to_attack(), data.timeout, position, data.tick_since)
        raise ValueError(f"Unsupported object type: {data.type!r}")
