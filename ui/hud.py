"""HUD szövegek és a populáció-grafikon rajzolása."""

from __future__ import annotations

import pygame

import config


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
        f"Novenyek: {len(sim.plants)}   Novenyevok: {len(sim.herbivores)}   Ragadozok: {len(sim.carnivores)}",
        f"FPS: {fps:.0f}   Sebesseg: {weather.time_scale:.1f}x",
    ]
    for i, line in enumerate(lines):
        text_surf = font.render(line, True, config.COLOR_TEXT)
        surface.blit(text_surf, (10, 8 + i * 18))


def draw_population_graph(surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, stats) -> None:
    pygame.draw.rect(surface, (22, 22, 29), rect)
    pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, rect, 1)

    title = font.render("Populacio", True, config.COLOR_TEXT_DIM)
    surface.blit(title, (rect.x + 4, rect.y - 18))

    series = [
        ("plants", config.COLOR_PLANT),
        ("herbivores", config.COLOR_HERBIVORE),
        ("carnivores", config.COLOR_CARNIVORE),
    ]
    max_val = stats.max_value()
    for key, color in series:
        data = stats.history[key]
        if len(data) < 2:
            continue
        n = len(data)
        points = []
        for i, value in enumerate(data):
            px = rect.x + (i / (stats.max_points - 1)) * rect.width
            py = rect.bottom - (value / max_val) * (rect.height - 4) - 2
            points.append((px, py))
        if len(points) >= 2:
            pygame.draw.lines(surface, color, False, points, 2)
