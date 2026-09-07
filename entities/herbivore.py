"""Növényevő: keresi a legközelebbi növényt, menekül a ragadozók elől."""

from __future__ import annotations

import config
from .mobile import MobileEntity


class Herbivore(MobileEntity):
    GENES = config.HERBIVORE_GENES
    RANGES = config.HERBIVORE_RANGES
    BASE_COLOR = config.COLOR_HERBIVORE

    def update(self, dt: float, sim) -> None:
        self.age += dt
        env = sim.environment
        temp = env.get_temperature(self.x, self.y)
        water = env.get_water(self.x, self.y)

        t_min, t_max = self.traits["temp_min"], self.traits["temp_max"]
        temp_stress = 0.0
        if temp < t_min:
            temp_stress = (t_min - temp) / 12.0
        elif temp > t_max:
            temp_stress = (temp - t_max) / 12.0

        metabolic_cost = self.traits["metabolism_rate"] * (1.0 + temp_stress) * (self.traits["size"] / 6.0)
        self.energy -= metabolic_cost * dt * self.max_energy * 0.012

        if water < self.traits["water_need"]:
            self.energy -= 0.15 * dt

        predator = sim.find_nearest(self, sim.carn_grid, self.traits["vision_range"])
        if predator is not None:
            self._flee_from(predator.x, predator.y, dt, speed_mult=1.0 + self.traits["flee_bonus"], env=env)
        else:
            food = sim.find_nearest(self, sim.plant_grid, self.traits["vision_range"])
            if food is not None:
                dist = self.distance_to(food)
                capture_range = self.traits["size"] + 3.0
                if dist < capture_range:
                    bite = min(self.traits["bite_size"], food.energy)
                    food.energy -= bite
                    self.energy = min(self.max_energy, self.energy + bite * 0.8)
                else:
                    self._move_towards(food.x, food.y, dt, env=env)
            else:
                self._wander(dt, env=env)

        self.reproduce_cooldown -= dt
        if self.energy > self.max_energy * 0.55 and self.reproduce_cooldown <= 0 and self.age > 50:
            mate = sim.find_mate(self, sim.herb_grid)
            if mate is not None:
                sim.reproduce_mobile(self, mate, sim.herbivores, config.MAX_HERBIVORES)
                self.energy *= 0.6
                mate.energy *= 0.6
                cooldown = 380.0 - self.traits["fertility"] * 260.0
                self.reproduce_cooldown = cooldown
                mate.reproduce_cooldown = cooldown

        self._clamp_to_world()

    def draw(self, surface) -> None:
        import pygame

        radius = int(self.traits["size"])
        pygame.draw.circle(surface, self.BASE_COLOR, (int(self.x), int(self.y)), radius)
        pygame.draw.circle(surface, (20, 20, 25), (int(self.x), int(self.y)), radius, 1)
