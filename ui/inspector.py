"""Entitás-részletező: kattintásra megjeleníti a kiválasztott egyed adatait
és DNS-kódját."""

from __future__ import annotations

import math

import pygame

import config

_SPECIES_NAMES = {
    "Plant": "Novenyi",
    "Herbivore": "Novenyevo",
    "Carnivore": "Ragadozo",
}


def find_clicked_entity(sim, pos: tuple[int, int]):
    px, py = pos
    best, best_dist = None, 14.0
    for group in (sim.plants, sim.herbivores, sim.carnivores):
        for entity in group:
            radius = entity.traits.get("size", 5.0)
            dist = math.hypot(entity.x - px, entity.y - py)
            if dist <= max(radius + 3.0, best_dist):
                if dist < best_dist:
                    best_dist = dist
                    best = entity
    return best


def draw_inspector(surface: pygame.Surface, rect: pygame.Rect, font: pygame.font.Font, entity) -> None:
    pygame.draw.rect(surface, (22, 22, 29), rect)
    pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, rect, 1)

    title = font.render("Kivalasztott egyed", True, config.COLOR_TEXT_DIM)
    surface.blit(title, (rect.x + 4, rect.y - 18))

    if entity is None or entity.is_dead():
        hint = font.render("Kattints egy entitasra a vilagban.", True, config.COLOR_TEXT_DIM)
        surface.blit(hint, (rect.x + 8, rect.y + 8))
        return

    species = _SPECIES_NAMES.get(type(entity).__name__, type(entity).__name__)
    lines = [
        f"Faj: {species}   Generacio: {entity.generation}",
        f"Kor: {entity.age:.0f}   Energia: {entity.energy:.0f}/{entity.max_energy:.0f}",
        f"DNS: {entity.genome.to_code_string()}",
        "-- tulajdonsagok --",
    ]
    # ket oszlopba rendezve, hogy a sok gén-tulajdonság is elférjen a panelen
    trait_items = list(entity.traits.items())
    for i in range(0, len(trait_items), 2):
        name_a, value_a = trait_items[i]
        cell = f"{name_a}: {value_a:.3f}"
        if i + 1 < len(trait_items):
            name_b, value_b = trait_items[i + 1]
            cell = f"{cell:<20}{name_b}: {value_b:.3f}"
        lines.append(cell)

    y = rect.y + 6
    for line in lines:
        color = config.COLOR_TEXT if not line.startswith("--") else config.COLOR_TEXT_DIM
        text_surf = font.render(line, True, color)
        surface.blit(text_surf, (rect.x + 8, y))
        y += 15
        if y > rect.bottom - 12:
            break
