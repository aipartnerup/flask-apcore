"""Test module providing a simple callable for RegistryWriter target resolution tests."""


def sample_handler(name: str, age: int) -> dict:
    """Handle a sample request."""
    return {"name": name, "age": age}
