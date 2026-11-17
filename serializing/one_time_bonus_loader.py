from bonuses import OneTimeBonus
from serializing.save_data import BonusData, ParamsData


class OneTimeBonusLoader:
    """Convert one-time bonuses to and from save data."""

    @staticmethod
    def save_to(bonus: OneTimeBonus) -> BonusData:
        """Capture a one-time bonus."""
        return BonusData(ParamsData.from_params(bonus.get_modifier()))

    @staticmethod
    def load_from(data: BonusData) -> OneTimeBonus:
        """Restore a one-time bonus."""
        return OneTimeBonus(data.modifier.to_params())
