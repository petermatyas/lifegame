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
    "Decomposer": "Lebonto",
}


def find_clicked_entity(sim, pos: tuple[int, int]):
    px, py = pos
    best, best_dist = None, 14.0
    for group in (sim.plants, sim.herbivores, sim.carnivores, sim.decomposers):
        for entity in group:
            radius = entity.traits.get("size", 5.0)
            dist = math.hypot(entity.x - px, entity.y - py)
            if dist <= max(radius + 3.0, best_dist):
                if dist < best_dist:
                    best_dist = dist
                    best = entity
    return best


_LINE_HEIGHT = 15
_DNS_LINE_INDEX = 3  # Faj, Allapot, Kor/Energia, DNS - lasd draw_inspector


def get_dns_line_rect(rect: pygame.Rect, entity) -> pygame.Rect | None:
    """A DNS-sor kattintható területe, hogy a főprogram el tudja dönteni,
    hogy egy kattintás a DNS-bontás ki/be kapcsolására irányult-e."""
    if entity is None:
        return None
    y = rect.y + 6 + _DNS_LINE_INDEX * _LINE_HEIGHT
    return pygame.Rect(rect.x + 4, y - 2, rect.width - 8, _LINE_HEIGHT)


def _environment_lines(entity, environment, weather) -> list[str]:
    """Az egyed aktualis poziciojara hato kornyezeti adatok - ugyanazok az
    ertekek, amiket a viselkedese (lasd Plant/Herbivore/... update()) is
    figyelembe vesz, hogy lathato legyen, mi hat ra eppen."""
    temp = environment.get_temperature(entity.x, entity.y)
    water = environment.get_water(entity.x, entity.y)
    humus = environment.get_humus(entity.x, entity.y)
    elevation_m = environment.elevation_to_meters(environment.get_elevation(entity.x, entity.y))
    pressure = environment.get_pressure(entity.x, entity.y)
    terrain = "allovizben" if environment.is_deep_water(entity.x, entity.y) else "szarazfoldon"
    sun = weather.sunlight_factor()
    day_state = "nappal" if weather.is_day() else "ejszaka"
    rain_state = "esik" if weather.raining else "szaraz"
    return [
        "-- helyi kornyezet (az egyed poziciojaban) --",
        f"Homerseklet: {temp:.1f} C   Viz: {water:.2f}   Humusz: {humus:.2f}",
        f"Magassag: {elevation_m:.0f} m   Legnyomas: {pressure:.0f} hPa   ({terrain})",
        f"Napfeny: {sun:.2f}   {day_state}, {rain_state}",
    ]


def draw_inspector(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font: pygame.font.Font,
    entity,
    dna_expanded: bool = False,
    environment=None,
    weather=None,
) -> None:
    pygame.draw.rect(surface, (22, 22, 29), rect)
    pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, rect, 1)

    title = font.render("Kivalasztott egyed", True, config.COLOR_TEXT_DIM)
    surface.blit(title, (rect.x + 4, rect.y - 18))

    if entity is None:
        hint = font.render("Kattints egy entitasra a vilagban.", True, config.COLOR_TEXT_DIM)
        surface.blit(hint, (rect.x + 8, rect.y + 8))
        return

    species = _SPECIES_NAMES.get(type(entity).__name__, type(entity).__name__)
    dns_code = entity.genome.to_code_string()
    dns_hint = "bezaras" if dna_expanded else "reszletek"
    lines = [
        f"Faj: {species}   Generacio: {entity.generation}",
        f"Allapot: {entity.state}",
        f"Kor: {entity.age:.0f}   Energia: {entity.energy:.0f}/{entity.max_energy:.0f}",
        f"DNS: {dns_code}  [kattints: {dns_hint}]",
    ]

    if environment is not None and weather is not None:
        lines.extend(_environment_lines(entity, environment, weather))

    if dna_expanded:
        # a DNS-kod minden karaktere egy-egy gennek felel meg (a genom
        # bejarasi sorrendjeben) - itt latszik, melyik karakter milyen
        # nyers (0-1) es tenyleges (skalazott) erteket kodol
        lines.append("-- DNS bontasa: poz:kar gen = nyers -> ertek --")
        gene_items = list(entity.genome.genes.items())
        for i, (name, raw) in enumerate(gene_items):
            char = dns_code[i] if i < len(dns_code) else "?"
            phenotype_val = entity.traits.get(name)
            if phenotype_val is not None:
                lines.append(f"{i:>2}:{char} {name} = {raw:.2f} -> {phenotype_val:.3f}")
            else:
                lines.append(f"{i:>2}:{char} {name} = {raw:.2f}  (nincs hatasa ennel a fajnal)")
    else:
        lines.append("-- tulajdonsagok --")
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
        y += _LINE_HEIGHT
        if y > rect.bottom - 12:
            break
