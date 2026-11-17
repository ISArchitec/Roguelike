from unittest.mock import MagicMock

import pytest

from map import Cell
from positioning import ICellObject, Position


@pytest.mark.parametrize(
    "is_wall, has_object, raises_error",
    [
        pytest.param(False, False, False, id="empty-passage"),
        pytest.param(False, True, False, id="occupied-passage"),
        pytest.param(True, False, False, id="empty-wall"),
        pytest.param(True, True, True, id="occupied-wall-rejected"),
    ],
)
def test_init(is_wall, has_object, raises_error):
    position = Position(2, 3)
    obj = MagicMock(spec=ICellObject) if has_object else None

    if raises_error:
        with pytest.raises(ValueError, match="A wall cannot contain an object"):
            Cell.create_from(position, obj, is_wall)
        return

    cell = Cell.create_from(position, obj, is_wall)

    assert cell.position is position
    assert cell.get_object() is obj
    assert cell.is_wall() is is_wall
    assert cell.empty() is (not has_object)


@pytest.mark.parametrize(
    "is_wall, occupant, expected",
    [
        pytest.param(False, "empty", True, id="add-to-empty-passage"),
        pytest.param(True, "empty", True, id="cell-leaves-wall-check-to-map"),
        pytest.param(False, "same", False, id="same-object-already-present"),
        pytest.param(False, "other", False, id="another-object-already-present"),
    ],
)
def test_add_cell_object(is_wall, occupant, expected):
    position = Position(2, 3)
    obj = MagicMock(spec=ICellObject)
    original = {"empty": None, "same": obj, "other": MagicMock(spec=ICellObject)}[occupant]
    cell = Cell.create_from(position, original, is_wall)

    assert cell.add_cell_object(obj) is expected

    assert cell.get_object() is (obj if expected else original)
    assert cell.check_in(obj) is (expected or occupant == "same")
    assert cell.position is position
    assert cell.is_wall() is is_wall


@pytest.mark.parametrize(
    "occupant, removed",
    [
        pytest.param("empty", False, id="remove-from-empty-cell"),
        pytest.param("same", True, id="remove-present-object"),
        pytest.param("other", False, id="keep-different-object"),
        pytest.param("equal", False, id="keep-equal-but-distinct-object"),
    ],
)
def test_remove_cell_object(occupant, removed):
    position = Position(2, 3)
    obj = MagicMock(spec=ICellObject)
    original = None if occupant == "empty" else obj if occupant == "same" else MagicMock(spec=ICellObject)
    if occupant == "equal":
        original.__eq__.return_value = True
        assert original == obj
        assert original is not obj
    cell = Cell.create_new(position)
    if original is not None:
        cell.add_cell_object(original)

    cell.remove_cell_object(obj)

    assert cell.get_object() is (None if removed else original)
    assert cell.empty() is (removed or occupant == "empty")
    assert cell.position is position
    assert not cell.is_wall()
    cell.remove_cell_object(obj)
    assert cell.get_object() is (None if removed else original)


@pytest.mark.parametrize(
    "is_wall, has_object, raises_error",
    [
        pytest.param(False, False, False, id="turn-empty-passage-into-wall"),
        pytest.param(True, False, False, id="keep-existing-wall"),
        pytest.param(False, True, True, id="reject-occupied-cell"),
    ],
)
def test_make_wall(is_wall, has_object, raises_error):
    position = Position(2, 3)
    obj = MagicMock(spec=ICellObject) if has_object else None
    cell = Cell.create_from(position, obj, is_wall)

    if raises_error:
        with pytest.raises(ValueError, match="An occupied cell cannot become a wall"):
            cell.make_wall()
    else:
        cell.make_wall()

    assert cell.is_wall() is (is_wall if raises_error else True)
    assert cell.get_object() is obj
    assert cell.position is position
    assert cell.empty() is (not has_object)
