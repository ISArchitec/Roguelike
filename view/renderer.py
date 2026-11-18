# ruff: noqa: RUF001
"""Render the game state as a compact top-down terminal display."""

import os
import shutil
import textwrap
from typing import TextIO

from bonuses import Certificate, IDCard
from hero import Hero
from monsters import BossMonster, Monster
from play_cycle import GlobalConfig
from play_cycle.game import Game
from positioning import ICellObject

_RESET = "\x1b[0m"
_CYAN = "\x1b[96m"
_DIM = "\x1b[90m"
_WALL = "\x1b[34m"
_RED = "\x1b[91m"
_GOLD = "\x1b[93m"
_GREEN = "\x1b[92m"
_TILE_WIDTH = 3
_TILE_HEIGHT = 3
_MAX_VIEW_WIDTH = 15
_MAX_VIEW_HEIGHT = 6
_PANEL_WIDTH = 27
_WALL_TILES = (("###", "#:#", "###"), ("###", "##:", "###"), ("###", ":##", "###"))
_FLOOR_TILES = (("   ", " . ", "   "), ("   ", " , ", "   "), ("   ", "   ", "   "))


def supports_ansi(stream: TextIO) -> bool:
    """Check whether the output terminal can display ANSI control sequences."""
    if not stream.isatty() or os.environ.get("TERM") == "dumb":
        return False
    if os.name != "nt":
        return True
    # Windows consoles need virtual terminal processing enabled before ANSI is used.
    import ctypes

    kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
    kernel.GetStdHandle.restype = ctypes.c_void_p
    kernel.GetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong))
    kernel.SetConsoleMode.argtypes = (ctypes.c_void_p, ctypes.c_ulong)
    handle = kernel.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode))) and bool(
        kernel.SetConsoleMode(handle, mode.value | 0x0004)
    )


def _paint(text: str, color: str, enabled: bool) -> str:
    return f"{color}{text}{_RESET}" if enabled else text


def _sprite(obj: ICellObject, symbol: str) -> tuple[tuple[str, str, str], str, str]:
    if isinstance(obj, Hero):
        return ("\\|/", f"-{symbol}-", "/|\\"), "герой", _CYAN
    if isinstance(obj, BossMonster):
        return ("/#\\", f"[{symbol}]", "\\#/"), "босс", _RED
    if isinstance(obj, Monster):
        return ("/^\\", f"|{symbol}|", "\\_/"), "враг", _RED
    if isinstance(obj, Certificate):
        return ("+-+", f"|{symbol}|", "+-+"), "справка", _GREEN
    if isinstance(obj, IDCard):
        return (".-.", f"|{symbol}|", "'-'"), "удостоверение", _GOLD
    return ("   ", f" {symbol} ", "   "), "объект", _GOLD


def render(game: Game, actions_used: int, cooldown: str, messages: list[str], colored: bool) -> str:
    """Draw the visible map, hero status, controls, and recent messages."""
    terminal = shutil.get_terminal_size(fallback=(80, 24))
    side_panel = terminal.columns >= 74
    available = terminal.columns - (_PANEL_WIDTH + 5 if side_panel else 4)
    game_map = game.get_map()
    width = min(_MAX_VIEW_WIDTH, game_map.get_width(), max(1, available // _TILE_WIDTH))
    # Leave room for the title, controls, and prompt on typical terminals.
    reserved_lines = 10 if side_panel else 16
    height = min(
        _MAX_VIEW_HEIGHT, game_map.get_height(), max(1, (terminal.lines - reserved_lines) // 3)
    )
    hero = game.get_hero()
    position = hero.get_position()
    left = max(0, min(position.get_x() - width // 2, game_map.get_width() - width))
    bottom = max(0, min(position.get_y() - height // 2, game_map.get_height() - height))
    cells = game_map.get_cells()
    config = GlobalConfig.get_instance()
    map_lines: list[str] = []
    for y in reversed(range(bottom, bottom + height)):
        rows = ["" for _ in range(_TILE_HEIGHT)]
        for x in range(left, left + width):
            cell = cells[y * game_map.get_width() + x]
            obj = cell.get_object()
            if cell.is_wall():
                sprite, color = _WALL_TILES[(x * 7 + y * 11) % len(_WALL_TILES)], _WALL
            elif obj is None:
                sprite, color = _FLOOR_TILES[(x * 13 + y * 7) % len(_FLOOR_TILES)], _DIM
            else:
                try:
                    symbol = config.get_object_view(obj)[:1] or "?"
                except KeyError:
                    symbol = "?"
                sprite, _, color = _sprite(obj, symbol)
            for index, line in enumerate(sprite):
                rows[index] += _paint(line, color, colored)
        map_lines.extend(rows)

    params = hero.get_params()
    panel = [
        " ПЕРСОНАЖ",
        f" Здоровье: {params.health}",
        f" Защита:  {params.defence}",
        f" Атака:    {params.attack}",
        f" Скорость: {params.speed}",
        f" Действий: {max(0, params.speed - actions_used)}",
        f" Спецатака: {cooldown}",
    ]
    frame = "+" + "-" * (width * _TILE_WIDTH) + "+"
    title = f" БЮРО / СЕКЦИЯ {game.get_section_passed() + 1} / ХОД {game.get_ticks() + 1} "
    lines = [_paint(title, _CYAN, colored), f" Врагов: {game.get_enemy_count()}"]
    lines.append(
        f" КАРТА  x: {left + 1}–{left + width} / {game_map.get_width()}  "
        f"y: {bottom + 1}–{bottom + height} / {game_map.get_height()}"
    )
    lines.append(_paint(frame, _WALL, colored))
    for index, row in enumerate(map_lines):
        line = _paint("|", _WALL, colored) + row + _paint("|", _WALL, colored)
        if side_panel and index < len(panel):
            color = _CYAN if index == 0 else _GREEN if index == 1 else _RESET
            line += "  " + _paint(panel[index][:_PANEL_WIDTH], color, colored)
        lines.append(line)
    lines.append(_paint(frame, _WALL, colored))
    if not side_panel:
        compact_panel = (
            f" Здоровье: {params.health}  Защита: {params.defence}"
            f"  Атака: {params.attack}  Скорость: {params.speed}\n"
            f" Действий: {max(0, params.speed - actions_used)}  Спецатака: {cooldown}"
        )
        for paragraph in compact_panel.splitlines():
            lines.extend(textwrap.wrap(paragraph, width=max(1, terminal.columns)))
    elif len(panel) > len(map_lines):
        lines.extend(panel[len(map_lines) :])
    controls = (
        "card N выбрать удостоверение | C удостоверения | WASD движение | "
        "X спецатака | I предметы | F справки | "
        "end закончить ход | save сохранить | q выход | help помощь"
    )
    lines.extend(
        _paint(line, _CYAN, colored)
        for line in textwrap.wrap(controls, width=max(1, terminal.columns))
    )
    if messages:
        lines.append(_paint(" СОБЫТИЯ: " + " | ".join(messages[-2:]), _GOLD, colored))
    return "\n".join(lines)
