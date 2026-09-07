"""Közös entitás-alaposztály minden faj számára."""

from __future__ import annotations

import itertools
import math
import random

from .genome import Genome

_id_counter = itertools.count(1)


class Entity:
    GENES: list[str] = []
    RANGES: dict[str, tuple[float, float]] = {}
    BASE_COLOR = (255, 255, 255)

    def __init__(self, x: float, y: float, genome: Genome, energy: float | None = None, generation: int = 0):
        self.id = next(_id_counter)
        self.x = x
        self.y = y
        self.genome = genome
        self.traits = genome.decode(self.RANGES)
        self.age = 0.0
        self.generation = generation
        self.alive = True
        self.reproduce_cooldown = random.uniform(0.0, 60.0)
        max_energy = self.traits.get("max_energy", 100.0)
        self.energy = energy if energy is not None else max_energy * 0.55

    @property
    def max_energy(self) -> float:
        return self.traits.get("max_energy", 100.0)

    @property
    def energy_ratio(self) -> float:
        return max(0.0, min(1.0, self.energy / self.max_energy))

    def is_dead(self) -> bool:
        if not self.alive or self.energy <= 0:
            return True
        lifespan = self.traits.get("lifespan")
        if lifespan is not None and self.age > lifespan:
            return True
        return False

    def update(self, dt: float, sim) -> None:
        raise NotImplementedError

    def draw(self, surface) -> None:
        raise NotImplementedError

    def distance_to(self, other: "Entity") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)
