"""Ragadozó: vadászik a növényevőkre, siker esélye attack_power vs. zsákmány
menekülési/álca tulajdonságaitól függ."""

from __future__ import annotations

import random

import config
from .mobile import MobileEntity


def _clamp(value: float, lo: float, hi: float) -> float:
    return lo if value < lo else hi if value > hi else value


class Carnivore(MobileEntity):
    GENES = config.CARNIVORE_GENES
    RANGES = config.CARNIVORE_RANGES
    BASE_COLOR = config.COLOR_CARNIVORE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attack_cooldown = 0.0

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

        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)

        prey = sim.find_nearest(self, sim.herb_grid, self.traits["vision_range"])
        if prey is not None:
            dist = self.distance_to(prey)
            capture_range = self.traits["size"] + prey.traits["size"]
            if dist < capture_range:
                if self.attack_cooldown <= 0:
                    prey_defense = prey.traits["flee_bonus"] * 0.5 + prey.traits["camouflage"] * 0.4
                    chance = _clamp(0.18 + (self.traits["attack_power"] - prey_defense) * 0.3, 0.03, 0.75)
                    self.energy -= 0.012 * self.max_energy
                    self.attack_cooldown = 22.0
                    if random.random() < chance:
                        self.energy = min(self.max_energy, self.energy + prey.energy * 0.75)
                        prey.alive = False
                        prey.energy = 0.0
            else:
                self._move_towards(prey.x, prey.y, dt, env=env)
        else:
            self._wander(dt, env=env)

        self.reproduce_cooldown -= dt
        if self.energy > self.max_energy * 0.6 and self.reproduce_cooldown <= 0 and self.age > 100:
            mate = sim.find_mate(self, sim.carn_grid)
            if mate is not None:
                sim.reproduce_mobile(self, mate, sim.carnivores, config.MAX_CARNIVORES)
                self.energy *= 0.55
                mate.energy *= 0.55
                cooldown = 420.0 - self.traits["fertility"] * 260.0
                self.reproduce_cooldown = cooldown
                mate.reproduce_cooldown = cooldown

        self._clamp_to_world()

    def draw(self, surface) -> None:
        import pygame

        radius = int(self.traits["size"])
        pygame.draw.circle(surface, self.BASE_COLOR, (int(self.x), int(self.y)), radius)
        pygame.draw.circle(surface, (20, 20, 25), (int(self.x), int(self.y)), radius, 1)
        tip = (int(self.x + radius * 0.9), int(self.y - radius * 0.9))
        pygame.draw.circle(surface, (255, 235, 200), tip, max(1, radius // 3))
