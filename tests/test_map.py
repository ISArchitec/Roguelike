from unittest.mock import MagicMock, call

import pytest

from hero import Hero
from map import Cell, Map
from play_cycle import IModelSubscriber
from positioning import Direction, ICellObject, Position


def make_object(x, y, inactive=False, spec=ICellObject):
    obj = MagicMock(spec=spec)
    obj.get_position.return_value = Position(x, y)
    obj.set_position.side_effect = lambda position: setattr(obj.get_position, "return_value", position)
    obj.is_inactive.return_value = inactive
    return obj


def make_map(width=3, height=3, hero_position=(2, 2), walls=(), objects=()):
    hero = make_object(*hero_position, spec=Hero)
    occupants = {hero_position: hero}
    occupants.update({(obj.get_position().get_x(), obj.get_position().get_y()): obj for obj in objects})
    cells = [
        Cell.create_from(Position(x, y), occupants.get((x, y)), (x, y) in walls)
        for y in range(height) for x in range(width)
    ]
    return Map.create_from(width, height, cells, hero, MagicMock(spec=IModelSubscriber))


@pytest.mark.parametrize("width, height", [(0, 1), (-1, 1), (1, 0), (1, -1), (0, 0)])
def test_reject_invalid_dimensions(width, height):
    with pytest.raises(ValueError, match="Map dimensions must be positive"):
        Map.create_from(width, height, [], make_object(0, 0, spec=Hero), MagicMock(spec=IModelSubscriber))


@pytest.mark.parametrize("count", [0, 5, 7])
def test_reject_wrong_cell_count(count):
    cells = [Cell.create_new(Position(index, 0)) for index in range(count)]
    with pytest.raises(ValueError, match=r"Map must contain exactly width \* height cells"):
        Map.create_from(3, 2, cells, make_object(0, 0, spec=Hero), MagicMock(spec=IModelSubscriber))


@pytest.mark.parametrize(
    "position, expected",
    [(None, False), (Position(-1, 0), False), (Position(3, 0), False),
     (Position(0, -1), False), (Position(0, 2), False),
     (Position(0, 0), True), (Position(2, 1), True)],
)
def test_is_valid_position(position, expected):
    game_map = make_map(3, 2, hero_position=(2, 1))
    assert game_map.is_valid_position(position) is expected


def test_get_hero():
    hero = make_object(0, 0, spec=Hero)
    game_map = Map.create_from(1, 1, [Cell.create_from(Position(0, 0), hero, False)], hero, MagicMock(spec=IModelSubscriber))
    assert game_map.get_hero() is hero


@pytest.mark.parametrize("position", [Position(0, 0), Position(1, 2)])
def test_get_hero_position(position):
    game_map = make_map()
    game_map.get_hero().set_position(position)
    assert game_map.get_hero_position() is position


@pytest.mark.parametrize("state, expected", [("empty", True), ("wall", False), ("occupied", False), ("outside", False)])
def test_add_object(state, expected):
    game_map = make_map(walls=[(0, 0)] if state == "wall" else [])
    position = {"empty": (0, 0), "wall": (0, 0), "occupied": (2, 2), "outside": (3, 0)}[state]
    assert game_map.add_object(make_object(*position)) is expected


def test_added_object_occupies_cell():
    game_map = make_map()
    game_map.add_object(make_object(0, 0))
    assert not game_map.add_object(make_object(0, 0))


@pytest.fixture(params=["outside-source", "absent-source", "other-source", "outside-target", "wall", "occupied", "free"])
def movement(request):
    state = request.param
    origin = (-1, 0) if state == "outside-source" else (0, 0)
    actor = make_object(*origin)
    objects = [] if state in ("outside-source", "absent-source") else [actor]
    if state == "other-source":
        objects = [make_object(0, 0)]
    if state == "occupied":
        objects.append(make_object(1, 0))
    game_map = make_map(walls=[(1, 0)] if state == "wall" else [], objects=objects)
    direction = Direction.LEFT if state == "outside-target" else Direction.RIGHT
    return game_map, actor, direction, state == "free"


def test_move_result(movement):
    game_map, actor, direction, expected = movement
    assert game_map.move(actor, direction) is expected


def test_move_position(movement):
    game_map, actor, direction, expected = movement
    origin = actor.get_position()
    game_map.move(actor, direction)
    target = origin.move(direction) if expected else origin
    assert (actor.get_position().get_x(), actor.get_position().get_y()) == (target.get_x(), target.get_y())


@pytest.mark.parametrize("position, available", [((0, 0), True), ((1, 0), False)])
def test_move_transfers_occupancy(position, available):
    actor = make_object(0, 0)
    game_map = make_map(objects=[actor])
    game_map.move(actor, Direction.RIGHT)
    assert game_map.add_object(make_object(*position)) is available


@pytest.mark.parametrize("state", ["wall", "occupied", "outside-target"])
def test_failed_move_keeps_source_occupied(state):
    actor = make_object(0, 0)
    objects = [actor, make_object(1, 0)] if state == "occupied" else [actor]
    game_map = make_map(objects=objects, walls=[(1, 0)] if state == "wall" else [])
    game_map.move(actor, Direction.LEFT if state == "outside-target" else Direction.RIGHT)
    assert not game_map.add_object(make_object(0, 0))


@pytest.mark.parametrize("direction, target", [(Direction.DOWN, (1, 0)), (Direction.UP, (1, 2)), (Direction.LEFT, (0, 1)), (Direction.RIGHT, (2, 1))])
def test_move_direction(direction, target):
    actor = make_object(1, 1)
    game_map = make_map(objects=[actor])
    game_map.move(actor, direction)
    assert (actor.get_position().get_x(), actor.get_position().get_y()) == target


@pytest.fixture(params=["adjacent", "direct"])
def interaction(request):
    def invoke(game_map, actor, position, force):
        if request.param == "direct":
            game_map.interact_direct(position, force)
        else:
            game_map.interact(actor, Direction.RIGHT, force)
    return invoke


@pytest.mark.parametrize("inactive", [False, True])
@pytest.mark.parametrize("force", [0, 7])
def test_interaction_passes_force(interaction, inactive, force):
    actor, target = make_object(0, 0), make_object(1, 0, inactive)
    game_map = make_map(objects=[actor, target])
    game_map.set_on_terminate_object(MagicMock())
    interaction(game_map, actor, Position(1, 0), force)
    target.interact.assert_called_once_with(force)


@pytest.mark.parametrize("inactive", [False, True])
def test_interaction_removes_only_inactive_target(interaction, inactive):
    actor, target = make_object(0, 0), make_object(1, 0, inactive)
    game_map = make_map(objects=[actor, target])
    game_map.set_on_terminate_object(MagicMock())
    interaction(game_map, actor, Position(1, 0), 7)
    assert game_map.add_object(make_object(1, 0)) is inactive


@pytest.mark.parametrize("inactive", [False, True])
def test_interaction_notifies_termination_once(interaction, inactive):
    actor, target = make_object(0, 0), make_object(1, 0, inactive)
    game_map = make_map(objects=[actor, target])
    callback = MagicMock()
    game_map.set_on_terminate_object(callback)
    interaction(game_map, actor, Position(1, 0), 7)
    interaction(game_map, actor, Position(1, 0), 7)
    assert callback.call_args_list == ([call()] if inactive else [])


def test_interaction_requires_callback(interaction):
    actor, target = make_object(0, 0), make_object(1, 0)
    game_map = make_map(objects=[actor, target])
    with pytest.raises(RuntimeError, match="Object termination callback has not been set"):
        interaction(game_map, actor, Position(1, 0), 7)
    target.interact.assert_not_called()


@pytest.mark.parametrize("state", ["outside-source", "absent-source", "other-source", "outside-target", "wall", "empty"])
def test_interact_ignores_invalid_attack(state):
    actor = make_object(-1 if state == "outside-source" else 0, 0)
    target = make_object(1, 0)
    objects = [target] if state in ("outside-source", "absent-source") else [actor, target]
    if state == "other-source":
        objects = [make_object(0, 0), target]
    if state in ("wall", "empty"):
        objects = [actor]
    game_map = make_map(objects=objects, walls=[(1, 0)] if state == "wall" else [])
    callback = MagicMock()
    game_map.set_on_terminate_object(callback)
    game_map.interact(actor, Direction.LEFT if state == "outside-target" else Direction.RIGHT, 7)
    target.interact.assert_not_called()
    callback.assert_not_called()


@pytest.mark.parametrize("position, walls", [(None, []), (Position(-1, 0), []), (Position(1, 0), [(1, 0)]), (Position(1, 0), [])])
def test_interact_direct_ignores_invalid_or_empty_target(position, walls):
    game_map = make_map(walls=walls)
    callback = MagicMock()
    game_map.set_on_terminate_object(callback)
    game_map.interact_direct(position, 7)
    callback.assert_not_called()


def test_replacing_termination_callback():
    target = make_object(1, 0, True)
    game_map = make_map(objects=[target])
    previous, current = MagicMock(), MagicMock()
    game_map.set_on_terminate_object(previous)
    game_map.set_on_terminate_object(current)
    game_map.interact_direct(Position(1, 0), 7)
    previous.assert_not_called()
    current.assert_called_once_with()


@pytest.mark.parametrize(
    "start, goal, walls, occupied, expected",
    [
        pytest.param(None, (2, 2), [], [], [], id="missing-start"),
        pytest.param((-1, 0), (2, 2), [], [], [], id="outside-start"),
        pytest.param((0, 0), (2, 2), [(0, 0)], [], [], id="wall-start"),
        pytest.param((2, 2), (2, 2), [], [], [], id="already-at-hero"),
        pytest.param((0, 0), (2, 0), [], [], [Direction.RIGHT, Direction.RIGHT], id="horizontal"),
        pytest.param((0, 2), (0, 0), [], [], [Direction.DOWN, Direction.DOWN], id="vertical"),
        pytest.param((2, 0), (0, 0), [], [], [Direction.LEFT, Direction.LEFT], id="left"),
        pytest.param((0, 0), (0, 2), [], [], [Direction.UP, Direction.UP], id="up"),
        pytest.param((0, 0), (2, 0), [(1, 0)], [], [Direction.UP, Direction.RIGHT, Direction.RIGHT, Direction.DOWN], id="wall-detour"),
        pytest.param((0, 0), (2, 0), [], [(1, 0)], [Direction.UP, Direction.RIGHT, Direction.RIGHT, Direction.DOWN], id="object-detour"),
        pytest.param((0, 0), (2, 2), [(1, 0), (0, 1)], [], [], id="unreachable"),
        pytest.param((0, 0), (2, 2), [], [], [Direction.UP, Direction.UP, Direction.RIGHT, Direction.RIGHT], id="equal-length-routes"),
    ],
)
def test_find_path_to_hero(start, goal, walls, occupied, expected):
    game_map = make_map(hero_position=goal, walls=walls, objects=[make_object(*position) for position in occupied])
    assert game_map.find_path_to_hero(None if start is None else Position(*start)) == expected


def test_find_path_from_occupied_cell():
    game_map = make_map(hero_position=(2, 0), objects=[make_object(0, 0)])
    assert game_map.find_path_to_hero(Position(0, 0)) == [Direction.RIGHT, Direction.RIGHT]


@pytest.mark.parametrize("state", ["wall", "empty", "occupied"])
def test_draw_cell(state):
    position = Position(0, 0)
    hero = make_object(0, 0, spec=Hero)
    console = MagicMock(spec=IModelSubscriber)
    cell = Cell.create_from(position, hero if state == "occupied" else None, state == "wall")
    game_map = Map.create_from(1, 1, [cell], hero, console)
    expected = {
        "wall": [call.draw_passage(position)],
        "empty": [],
        "occupied": [call.draw_object(hero)],
    }

    game_map.draw()

    assert console.method_calls == expected[state]


@pytest.mark.parametrize("states", [
    ("wall", "empty", "occupied"),
    ("occupied", "wall", "empty"),
    ("empty", "occupied", "wall"),
])
def test_draw_visits_all_cells_in_order(states):
    console = MagicMock(spec=IModelSubscriber)
    hero = make_object(states.index("occupied"), 0, spec=Hero)
    positions = [Position(x, 0) for x in range(3)]
    cells = [
        Cell.create_from(position, hero if state == "occupied" else None, state == "wall")
        for position, state in zip(positions, states)
    ]
    game_map = Map.create_from(3, 1, cells, hero, console)
    expected = [
        call.draw_passage(position) if state == "wall" else call.draw_object(hero)
        for position, state in zip(positions, states) if state != "empty"
    ]

    game_map.draw()

    assert console.method_calls == expected
