"""Test module providing simple callables for RegistryWriter target resolution tests."""

from pydantic import BaseModel


def sample_handler(name: str, age: int) -> dict:
    """Handle a sample request."""
    return {"name": name, "age": age}


class ItemCreate(BaseModel):
    title: str
    description: str = ""
    done: bool = False


class Item(BaseModel):
    id: int
    title: str
    description: str
    done: bool


def create_item(body: ItemCreate) -> Item:
    """Create a new item."""
    return Item(id=1, title=body.title, description=body.description, done=body.done)


def update_item(item_id: int, body: ItemCreate) -> Item:
    """Update an existing item."""
    return Item(id=item_id, title=body.title, description=body.description, done=body.done)
