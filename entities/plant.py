"""Növény: helyhez kötött, fotoszintézissel táplálkozó entitás."""

from __future__ import annotations

import math
import random

import config
from .base import Entity


class Plant(Entity):
    GENES = config.PLANT_GENES
    RANGES = config.PLANT_RANGES
    BASE_COLOR = config.COLOR_PLANT

    def update(self, dt: float, sim) -> None:
        self.age += dt
        env = sim.environment
        temp = env.get_temperature(self.x, self.y)
        water = env.get_water(self.x, self.y)
        sun = sim.weather.sunlight_factor()
        if sim.weather.raining:
            sun *= 0.6  # felhős, esős időben kevesebb napfény

        t_min, t_max = self.traits["temp_min"], self.traits["temp_max"]
        t_opt = (t_min + t_max) / 2.0
        t_half_range = max(1e-3, (t_max - t_min) / 2.0)
        temp_factor = max(0.0, 1.0 - ((temp - t_opt) / t_half_range) ** 2)

        water_need = self.traits["water_need"]
        water_factor = min(1.0, water / water_need) if water_need > 0 else 1.0
        drought_resistance = self.traits["drought_resistance"]
        if water < water_need:
            water_factor = max(water_factor, drought_resistance * 0.6)

        growth = self.traits["growth_rate"] * temp_factor * water_factor * (0.3 + 0.7 * sun) * dt
        self.energy = min(self.max_energy, self.energy + growth * self.max_energy)

        # elhervadás szélsőséges hőmérsékletben / tartós vízhiányban
        if temp_factor <= 0.03 or (water < water_need * 0.2 and drought_resistance < 0.25):
            self.energy -= 0.5 * dt * self.max_energy * 0.05

        self.reproduce_cooldown -= dt
        if self.energy > self.max_energy * 0.75 and self.reproduce_cooldown <= 0:
            sim.spawn_plant_seed(self)
            self.energy *= 0.55
            self.reproduce_cooldown = 140.0 + random.uniform(0.0, 120.0)

    def draw(self, surface) -> None:
        import pygame

        ratio = self.energy_ratio
        radius = 2 + int(ratio * 3)
        r, g, b = self.BASE_COLOR
        color = (int(r * (0.4 + 0.6 * ratio)), int(g * (0.5 + 0.5 * ratio)), int(b * (0.4 + 0.6 * ratio)))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), radius)
