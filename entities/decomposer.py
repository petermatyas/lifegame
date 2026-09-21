"""Lebontó szervezet: nagyon lassan mozog, az elhullott állatok/növények
detritusát keresi és bontja le humusszá, amit a növények tápanyagként
hasznosítanak."""

from __future__ import annotations

import config
from . import states
from .mobile import MobileEntity


class Decomposer(MobileEntity):
    GENES = config.DECOMPOSER_GENES
    RANGES = config.DECOMPOSER_RANGES
    BASE_COLOR = config.COLOR_DECOMPOSER
    CORPSE_RATIO = config.DECOMPOSER_CORPSE_RATIO

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
            self.energy -= 0.08 * dt

        hungry = self.energy_ratio < config.HUNGRY_ENERGY_RATIO
        food = sim.find_nearest(self, sim.detritus_grid, self.traits["vision_range"])
        if food is not None:
            dist = self.distance_to(food)
            capture_range = self.traits["size"] + 4.0
            if dist < capture_range:
                consumed = min(self.traits["decomposition_rate"] * dt, food.energy)
                food.energy -= consumed
                env.add_humus(self.x, self.y, consumed * self.traits["humus_yield"])
                self.energy = min(self.max_energy, self.energy + consumed * 0.4)
                self.state = states.DECOMPOSING
            else:
                self._move_towards(food.x, food.y, dt, env=env)
                self.state = states.HUNGRY if hungry else states.SEEKING_FOOD
        elif hungry:
            self._wander(dt, env=env)
            self.state = states.HUNGRY
        elif not sim.weather.is_day() and self.energy_ratio > config.SLEEP_MIN_ENERGY_RATIO:
            self._rest(dt)
            self.state = states.SLEEPING
        else:
            self._wander(dt, env=env)
            self.state = states.WANDER

        self.reproduce_cooldown -= dt
        if self.energy > self.max_energy * 0.6 and self.reproduce_cooldown <= 0 and self.age > 60:
            mate = sim.find_mate(self, sim.decomposer_grid)
            if mate is not None:
                sim.reproduce_mobile(self, mate, sim.decomposers, config.MAX_DECOMPOSERS)
                self.energy *= 0.6
                mate.energy *= 0.6
                cooldown = 320.0 - self.traits["fertility"] * 220.0
                self.reproduce_cooldown = cooldown
                mate.reproduce_cooldown = cooldown
                self.state = states.MATING
                mate.state = states.MATING

        self._clamp_to_world()

    def draw(self, surface) -> None:
        import pygame

        ratio = self.energy_ratio
        radius = int(self.traits["size"])
        pos = (int(self.x), int(self.y))
        if self.state == states.DEAD:
            color = (90, 90, 90)
        else:
            r, g, b = self.BASE_COLOR
            dim = 0.5 if self.state == states.SLEEPING else 1.0
            color = (int(r * (0.5 + 0.5 * ratio) * dim), int(g * (0.5 + 0.5 * ratio) * dim), int(b * (0.5 + 0.5 * ratio) * dim))
        pygame.draw.circle(surface, color, pos, radius)
        pygame.draw.circle(surface, (30, 24, 16), pos, radius, 1)
