from unittest.mock import MagicMock

import pytest

from hero import Hero
from map import MapBuilder
from play_cycle import IModelSubscriber
from positioning import ICellObject, Position


def make_object(position, spec=ICellObject):
    obj = MagicMock(spec=spec)
    obj.get_position.return_value = position
    return obj


@pytest.mark.parametrize(
    "width, height, valid",
    [
        pytest.param(1, 1, True, id="single-cell"),
        pytest.param(3, 2, True, id="wide-map"),
        pytest.param(2, 3, True, id="tall-map"),
        pytest.param(0, 2, False, id="zero-width"),
        pytest.param(-1, 2, False, id="negative-width"),
        pytest.param(2, 0, False, id="zero-height"),
        pytest.param(2, -1, False, id="negative-height"),
        pytest.param(0, 0, False, id="both-zero"),
    ],
)
def test_new(width, height, valid):
    if not valid:
        with pytest.raises(ValueError, match="Map dimensions must be positive"):
            MapBuilder.new(width, height)
        return

    builder = MapBuilder.new(width, height)
    hero = make_object(Position(width - 1, height - 1), Hero)
    builder.add_hero(hero)
    result = builder.to_map(MagicMock(spec=IModelSubscriber))
    assert result.is_valid_position(Position(width - 1, height - 1))
    assert not result.is_valid_position(Position(width, height - 1))
    assert not result.is_valid_position(Position(width - 1, height))


@pytest.mark.parametrize(
    "state, error",
    [
        pytest.param("wall", "Wall cannot be placed in a wall", id="existing-wall"),
        pytest.param("empty-passage", None, id="empty-passage"),
        pytest.param(
            "occupied-passage", "An occupied cell cannot become a wall", id="occupied-passage"
        ),
    ],
)
def test_add_passage(state, error):
    builder = MapBuilder.new(3, 2)
    position = Position(1, 1)
    obj = make_object(position)
    if state == "wall":
        builder.add_passage(position)
    elif state == "occupied-passage":
        builder.add_object(obj)

    if error:
        with pytest.raises(ValueError, match=error):
            builder.add_passage(position)
    else:
        builder.add_passage(position)

    expected_error = (
        "Cell is already occupied"
        if state == "occupied-passage"
        else "Object cannot be placed in a wall"
    )
    with pytest.raises(ValueError, match=expected_error):
        builder.add_object(make_object(position))


@pytest.mark.parametrize(
    "state, error",
    [
        pytest.param("empty", None, id="add-to-empty-cell"),
        pytest.param("wall", "Object cannot be placed in a wall", id="reject-wall"),
        pytest.param("same", "Cell is already occupied", id="reject-same-object"),
        pytest.param("other", "Cell is already occupied", id="reject-other-object"),
    ],
)
def test_add_object(state, error):
    builder = MapBuilder.new(3, 2)
    obj = make_object(Position(2, 1))
    original = obj if state == "same" else make_object(Position(2, 1))
    if state == "wall":
        builder.add_passage(Position(2, 1))
    elif state in ("same", "other"):
        builder.add_object(original)

    if error:
        with pytest.raises(ValueError, match=error):
            builder.add_object(obj)
    else:
        builder.add_object(obj)

    expected_error = (
        "Object cannot be placed in a wall" if state == "wall" else "Cell is already occupied"
    )
    with pytest.raises(ValueError, match=expected_error):
        builder.add_object(make_object(Position(2, 1)))


@pytest.mark.parametrize("method", ["add_passage", "add_object", "add_hero"])
@pytest.mark.parametrize(
    "position",
    [
        pytest.param(None, id="missing-position"),
        pytest.param(Position(-1, 0), id="left-of-map"),
        pytest.param(Position(3, 0), id="right-of-map"),
        pytest.param(Position(0, -1), id="below-map"),
        pytest.param(Position(0, 2), id="above-map"),
    ],
)
def test_reject_outside_position(method, position):
    builder = MapBuilder.new(3, 2)
    argument = (
        position
        if method == "add_passage"
        else make_object(position, Hero if method == "add_hero" else ICellObject)
    )

    with pytest.raises(ValueError, match="Position is outside the map"):
        getattr(builder, method)(argument)


@pytest.mark.parametrize(
    "state, error",
    [
        pytest.param("empty", None, id="add-first-hero"),
        pytest.param("wall", "Object cannot be placed in a wall", id="reject-wall"),
        pytest.param("occupied", "Cell is already occupied", id="reject-occupied-cell"),
        pytest.param("same-hero", "Hero has already been added", id="reject-same-hero"),
        pytest.param("other-hero", "Hero has already been added", id="reject-second-hero"),
    ],
)
def test_add_hero(state, error):
    builder = MapBuilder.new(3, 2)
    hero = make_object(Position(2, 1), Hero)
    original = make_object(Position(0, 0), Hero)
    occupant = make_object(Position(2, 1))
    if state == "wall":
        builder.add_passage(Position(2, 1))
    elif state == "occupied":
        builder.add_object(occupant)
    elif state == "same-hero":
        builder.add_hero(hero)
    elif state == "other-hero":
        builder.add_hero(original)

    if error:
        with pytest.raises(ValueError, match=error):
            builder.add_hero(hero)
    else:
        builder.add_hero(hero)
        console = MagicMock(spec=IModelSubscriber)
        assert builder.to_map(console).get_hero() is hero
        occupied = Position(2, 1)
        free = Position(0, 0)
        with pytest.raises(ValueError, match="Cell is already occupied"):
            builder.add_object(make_object(occupied))
        builder.add_object(make_object(free))


@pytest.mark.parametrize("has_hero", [False, True])
def test_to_map(has_hero):
    builder = MapBuilder.new(3, 2)
    console = MagicMock(spec=IModelSubscriber)
    hero = make_object(Position(0, 0), Hero)
    obj = make_object(Position(2, 1))
    builder.add_object(obj)
    builder.add_passage(Position(1, 0))
    if has_hero:
        builder.add_hero(hero)
    else:
        with pytest.raises(ValueError, match="Hero must be added before building the map"):
            builder.to_map(console)
        builder.add_hero(hero)

    result = builder.to_map(console)

    assert result.get_hero() is hero
    assert result.is_valid_position(Position(2, 1))
    assert not result.is_valid_position(Position(3, 1))
    assert not result.is_valid_position(Position(2, 2))
    assert not result.add_object(make_object(Position(0, 0)))
    assert not result.add_object(make_object(Position(1, 0)))
    assert not result.add_object(make_object(Position(2, 1)))
    assert result.add_object(make_object(Position(1, 1)))
