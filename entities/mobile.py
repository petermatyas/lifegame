"""Mozgó entitások (növényevők, ragadozók) közös mozgás-logikája."""

from __future__ import annotations

import math
import random

import config
from .base import Entity


class MobileEntity(Entity):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wander_dir = random.uniform(0.0, 2 * math.pi)

    def _move_towards(self, target_x: float, target_y: float, dt: float, speed: float | None = None) -> None:
        dx, dy = target_x - self.x, target_y - self.y
        dist = math.hypot(dx, dy) or 1e-6
        sp = speed if speed is not None else self.traits["speed"]
        step = sp * dt * config.MOVE_SCALE
        self.x += dx / dist * step
        self.y += dy / dist * step
        self.energy -= 0.006 * sp * dt

    def _flee_from(self, threat_x: float, threat_y: float, dt: float, speed_mult: float = 1.0) -> None:
        dx, dy = self.x - threat_x, self.y - threat_y
        dist = math.hypot(dx, dy) or 1e-6
        sp = self.traits["speed"] * speed_mult
        step = sp * dt * config.MOVE_SCALE
        self.x += dx / dist * step
        self.y += dy / dist * step
        self.energy -= 0.012 * sp * dt

    def _wander(self, dt: float) -> None:
        if random.random() < 0.05:
            self.wander_dir += random.uniform(-1.3, 1.3)
        sp = self.traits["speed"] * 0.4
        step = sp * dt * config.MOVE_SCALE
        self.x += math.cos(self.wander_dir) * step
        self.y += math.sin(self.wander_dir) * step
        self.energy -= 0.002 * sp * dt

    def _clamp_to_world(self) -> None:
        bounced = False
        if self.x < 0:
            self.x = 0
            bounced = True
        elif self.x > config.SIM_WIDTH:
            self.x = config.SIM_WIDTH
            bounced = True
        if self.y < 0:
            self.y = 0
            bounced = True
        elif self.y > config.SIM_HEIGHT:
            self.y = config.SIM_HEIGHT
            bounced = True
        if bounced:
            self.wander_dir = random.uniform(0.0, 2 * math.pi)
