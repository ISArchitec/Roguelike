class RandomLevelGeneratorLoader:
    """Placeholder until a concrete level generator is implemented."""

    @staticmethod
    def save_to(generator):
        """Return a placeholder for the generator state."""
        return None

    @staticmethod
    def load_from(data, generator):
        """Use a generator supplied by the caller until persistence is implemented."""
        if data is not None or generator is None:
            raise ValueError("A level generator must be supplied")
        return generator
