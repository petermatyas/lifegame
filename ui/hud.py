"""HUD szövegek és a populáció / környezet grafikonjainak rajzolása."""

from __future__ import annotations

import pygame

import config


def _alive_count(entities: list) -> int:
    return sum(1 for e in entities if not e.pending_removal)


def draw_hud(surface: pygame.Surface, font: pygame.font.Font, sim, fps: float) -> None:
    weather = sim.weather
    day = int(sim.tick_count // weather.day_length) + 1
    hour = weather.time_of_day * 24.0
    status_bits = []
    if weather.raining:
        status_bits.append("ESO")
    if weather.paused:
        status_bits.append("SZUNET")
    status = "  ".join(status_bits)

    lines = [
        f"Nap {day}  --  {hour:04.1f} h  --  {status}",
        f"Novenyek: {_alive_count(sim.plants)}   Novenyevok: {_alive_count(sim.herbivores)}   "
        f"Ragadozok: {_alive_count(sim.carnivores)}   Lebontok: {_alive_count(sim.decomposers)}",
        f"FPS: {fps:.0f}   Sebesseg: {weather.time_scale:.1f}x",
    ]
    for i, line in enumerate(lines):
        text_surf = font.render(line, True, config.COLOR_TEXT)
        surface.blit(text_surf, (10, 8 + i * 18))


def draw_map_legend(
    surface: pygame.Surface, font: pygame.font.Font, pos: tuple[int, int],
    color_lo: tuple[int, int, int], color_hi: tuple[int, int, int],
    val_lo: float, val_hi: float, fmt: str,
) -> None:
    """A térkép-szűrő (pl. hőmérséklet) szín-skáláját rajzolja ki egy
    függőleges sávként, a sáv aljára/tetejére írva, milyen tényleges
    értéknek felel meg az adott szín."""
    x, y = pos
    bar_width, bar_height = 18, 100
    steps = 32
    for i in range(steps):
        t = i / (steps - 1)
        color = tuple(int(lo + (hi - lo) * t) for lo, hi in zip(color_lo, color_hi))
        step_h = bar_height / steps
        step_y = y + bar_height - (i + 1) * step_h
        pygame.draw.rect(surface, color, (x, step_y, bar_width, step_h + 1))
    pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, (x, y, bar_width, bar_height), 1)

    hi_label = font.render(fmt.format(val_hi), True, (255, 255, 255))
    lo_label = font.render(fmt.format(val_lo), True, (255, 255, 255))
    surface.blit(hi_label, (x + bar_width + 4, y - 2))
    surface.blit(lo_label, (x + bar_width + 4, y + bar_height - lo_label.get_height() + 2))


def _draw_grid(surface: pygame.Surface, rect: pygame.Rect, lines: int = 3) -> None:
    for i in range(1, lines):
        gy = rect.y + rect.height * i / lines
        pygame.draw.line(surface, (40, 40, 50), (rect.x, gy), (rect.right, gy), 1)


def _draw_value_labels(
    surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font,
    min_val: float, max_val: float, fmt: str, color=None, side: str = "right",
) -> None:
    """Az adott sor (min/max mennyiség) számértékét írja ki a grafikon
    szélére, hogy a vonalak ne csak alakot, hanem tényleges értéket is
    mutassanak."""
    color = color or config.COLOR_TEXT_DIM
    top_surf = font.render(fmt.format(max_val), True, color)
    bottom_surf = font.render(fmt.format(min_val), True, color)
    if side == "right":
        tx = rect.right - top_surf.get_width() - 3
        bx = rect.right - bottom_surf.get_width() - 3
    else:
        tx = rect.x + 3
        bx = rect.x + 3
    surface.blit(top_surf, (tx, rect.y + 2))
    surface.blit(bottom_surf, (bx, rect.bottom - bottom_surf.get_height() - 2))


def _draw_time_axis(surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, point_count: int) -> None:
    """Az x tengely mennyiségét (hány tick van megjelenítve) írja ki."""
    left_surf = font.render(f"-{point_count} tick", True, config.COLOR_TEXT_DIM)
    right_surf = font.render("most", True, config.COLOR_TEXT_DIM)
    surface.blit(left_surf, (rect.x, rect.bottom + 3))
    surface.blit(right_surf, (rect.right - right_surf.get_width(), rect.bottom + 3))


def _plot_series(
    surface: pygame.Surface, rect: pygame.Rect, data: list[float], color,
    lo: float, hi: float, max_points: int,
) -> None:
    if len(data) < 2:
        return
    span = max(hi - lo, 1e-6)
    points = []
    for i, value in enumerate(data):
        px = rect.x + (i / (max_points - 1)) * rect.width
        py = rect.bottom - ((value - lo) / span) * (rect.height - 4) - 2
        points.append((px, py))
    pygame.draw.lines(surface, color, False, points, 2)


def draw_population_graph(surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, stats) -> None:
    pygame.draw.rect(surface, (22, 22, 29), rect)
    pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, rect, 1)

    title = font.render("Populacio", True, config.COLOR_TEXT_DIM)
    surface.blit(title, (rect.x + 4, rect.y - 18))

    _draw_grid(surface, rect)

    keys = ["plants", "herbivores", "carnivores", "decomposers"]
    colors = [config.COLOR_PLANT, config.COLOR_HERBIVORE, config.COLOR_CARNIVORE, config.COLOR_DECOMPOSER]
    max_val = stats.max_value(keys)
    for key, color in zip(keys, colors):
        _plot_series(surface, rect, stats.history[key], color, 0.0, max_val, stats.max_points)

    _draw_value_labels(surface, rect, font, 0.0, max_val, "{:.0f} db")
    _draw_time_axis(surface, rect, font, stats.max_points)


def draw_environment_graph(surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, stats) -> None:
    pygame.draw.rect(surface, (22, 22, 29), rect)
    pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, rect, 1)

    title = font.render("Kornyezet: hom.(C) / viz / humusz", True, config.COLOR_TEXT_DIM)
    surface.blit(title, (rect.x + 4, rect.y - 18))

    _draw_grid(surface, rect)

    temp_color = (230, 160, 70)
    water_color = (90, 150, 235)
    humus_color = config.COLOR_DECOMPOSER

    temp_data = stats.history["temperature"]
    water_data = stats.history["water"]
    humus_data = stats.history["humus"]

    if temp_data:
        t_lo, t_hi = min(temp_data), max(temp_data)
        if t_hi - t_lo < 1.0:
            t_lo -= 0.5
            t_hi += 0.5
        _plot_series(surface, rect, temp_data, temp_color, t_lo, t_hi, stats.max_points)
        _draw_value_labels(surface, rect, font, t_lo, t_hi, "{:.0f}C", color=temp_color, side="left")

    if water_data:
        w_lo, w_hi = min(water_data), max(water_data)
        if w_hi - w_lo < 0.02:
            w_lo -= 0.01
            w_hi += 0.01
        _plot_series(surface, rect, water_data, water_color, w_lo, w_hi, stats.max_points)
        _draw_value_labels(surface, rect, font, w_lo, w_hi, "{:.2f}", color=water_color, side="right")

    if humus_data:
        h_lo, h_hi = 0.0, max(0.05, max(humus_data))
        _plot_series(surface, rect, humus_data, humus_color, h_lo, h_hi, stats.max_points)

    _draw_time_axis(surface, rect, font, stats.max_points)
