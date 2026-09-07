"""A szimuláció fő motorja: entitások életciklusa, szaporodás,
szomszéd-keresés és a tick-enkénti update-sorrend."""

from __future__ import annotations

import math
import random

import config
from entities.genome import Genome
from entities.plant import Plant
from entities.herbivore import Herbivore
from entities.carnivore import Carnivore
from world.environment import Environment
from world.weather import Weather
from world.grid import SpatialGrid

from .stats import StatsTracker


class Simulation:
    def __init__(self):
        self.width = config.SIM_WIDTH
        self.height = config.SIM_HEIGHT

        self.environment = Environment()
        self.weather = Weather()

        self.mutation_rate = config.DEFAULT_MUTATION_RATE
        self.mutation_strength = config.DEFAULT_MUTATION_STRENGTH

        self.plants: list[Plant] = []
        self.herbivores: list[Herbivore] = []
        self.carnivores: list[Carnivore] = []

        self.plant_grid = SpatialGrid(self.width, self.height, cell_size=40)
        self.herb_grid = SpatialGrid(self.width, self.height, cell_size=50)
        self.carn_grid = SpatialGrid(self.width, self.height, cell_size=60)

        self.tick_count = 0.0
        self.stats = StatsTracker()

        self.selected_entity = None

        self._populate_initial()

    # ------------------------------------------------------------------ #
    # Népesítés / spawnolás
    # ------------------------------------------------------------------ #
    def _populate_initial(self) -> None:
        for _ in range(config.INITIAL_PLANTS):
            self.plants.append(self._make_random(Plant))
        for _ in range(config.INITIAL_HERBIVORES):
            self.herbivores.append(self._make_random(Herbivore))
        for _ in range(config.INITIAL_CARNIVORES):
            self.carnivores.append(self._make_random(Carnivore))

    def _make_random(self, cls, x: float | None = None, y: float | None = None):
        if x is None:
            x = random.uniform(0, self.width)
        if y is None:
            y = random.uniform(0, self.height)
        genome = Genome.random(cls.GENES)
        return cls(x, y, genome)

    def spawn_entity(self, species: str, x: float, y: float) -> None:
        species = species.lower()
        if species == "plant" and len(self.plants) < config.MAX_PLANTS:
            self.plants.append(self._make_random(Plant, x, y))
        elif species == "herbivore" and len(self.herbivores) < config.MAX_HERBIVORES:
            self.herbivores.append(self._make_random(Herbivore, x, y))
        elif species == "carnivore" and len(self.carnivores) < config.MAX_CARNIVORES:
            self.carnivores.append(self._make_random(Carnivore, x, y))

    def spawn_plant_seed(self, parent: Plant) -> None:
        if len(self.plants) >= config.MAX_PLANTS:
            return
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(6.0, parent.traits["seed_spread"])
        x = min(max(parent.x + math.cos(angle) * dist, 0), self.width)
        y = min(max(parent.y + math.sin(angle) * dist, 0), self.height)
        genome = parent.genome.copy_mutated(self.mutation_rate, self.mutation_strength)
        child = Plant(x, y, genome, generation=parent.generation + 1)
        self.plants.append(child)

    def reproduce_mobile(self, a, b, container: list, cap: int) -> None:
        if len(container) >= cap:
            return
        child_genome = a.genome.crossover(b.genome).mutate(self.mutation_rate, self.mutation_strength)
        cx = min(max((a.x + b.x) / 2 + random.uniform(-8, 8), 0), self.width)
        cy = min(max((a.y + b.y) / 2 + random.uniform(-8, 8), 0), self.height)
        child = type(a)(cx, cy, child_genome, generation=max(a.generation, b.generation) + 1)
        container.append(child)

    # ------------------------------------------------------------------ #
    # Szomszéd-keresés
    # ------------------------------------------------------------------ #
    def find_nearest(self, entity, grid: SpatialGrid, max_range: float):
        best, best_dist = None, max_range
        for candidate in grid.query_radius(entity.x, entity.y, max_range):
            if candidate is entity or not candidate.alive:
                continue
            dist = entity.distance_to(candidate)
            if dist < best_dist:
                best_dist = dist
                best = candidate
        return best

    def find_mate(self, entity, grid: SpatialGrid):
        best, best_dist = None, entity.traits["vision_range"]
        for candidate in grid.query_radius(entity.x, entity.y, best_dist):
            if candidate is entity or not candidate.alive:
                continue
            if candidate.reproduce_cooldown > 0 or candidate.age < 60:
                continue
            if candidate.energy < candidate.max_energy * 0.5:
                continue
            dist = entity.distance_to(candidate)
            if dist < best_dist:
                best_dist = dist
                best = candidate
        return best

    # ------------------------------------------------------------------ #
    # Fő ciklus
    # ------------------------------------------------------------------ #
    def update(self, real_dt_frames: float = 1.0) -> None:
        if self.weather.paused:
            return
        dt = real_dt_frames * self.weather.time_scale
        self._step(dt)

    def step_once(self) -> None:
        self._step(1.0)

    def _step(self, dt: float) -> None:
        self.tick_count += dt
        self.weather.update(dt)
        self.environment.update(dt, self.weather)

        self.plant_grid.build(self.plants)
        self.herb_grid.build(self.herbivores)
        self.carn_grid.build(self.carnivores)

        for plant in self.plants:
            plant.update(dt, self)
        for herbivore in self.herbivores:
            herbivore.update(dt, self)
        for carnivore in self.carnivores:
            carnivore.update(dt, self)

        self._cleanup()
        self._handle_migration(dt)
        self.stats.record(self)

    def _cleanup(self) -> None:
        self.plants = [e for e in self.plants if not e.is_dead()]
        self.herbivores = [e for e in self.herbivores if not e.is_dead()]
        self.carnivores = [e for e in self.carnivores if not e.is_dead()]
        if self.selected_entity is not None and self.selected_entity.is_dead():
            self.selected_entity = None

    def _handle_migration(self, dt: float) -> None:
        """Kis eséllyel "bevándorló" egyedek jelennek meg, ha egy populáció
        majdnem kihalt. Egy ilyen kis bekerített világban a ragadozók
        könnyen felszámolhatnák a teljes zsákmány-populációt (nincs térbeli
        menedék); ez a mechanizmus a szomszédos területekről történő
        természetes bevándorlást modellezi, hogy az ökoszisztéma tartósan
        fennmaradhasson végleges kihalás helyett."""
        if len(self.plants) < 25 and random.random() < 0.02 * dt:
            self.plants.append(self._make_random(Plant))
        if len(self.herbivores) < 6 and random.random() < 0.01 * dt:
            self.herbivores.append(self._make_random(Herbivore))
        if len(self.carnivores) < 3 and len(self.herbivores) > 12 and random.random() < 0.006 * dt:
            self.carnivores.append(self._make_random(Carnivore))

    def reset(self) -> None:
        self.__init__()
