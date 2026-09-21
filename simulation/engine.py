"""A szimuláció fő motorja: entitások életciklusa, szaporodás,
szomszéd-keresés és a tick-enkénti update-sorrend."""

from __future__ import annotations

import math
import random

import config
from entities import states
from entities.genome import Genome
from entities.plant import Plant
from entities.herbivore import Herbivore
from entities.carnivore import Carnivore
from entities.decomposer import Decomposer
from world.environment import Environment
from world.weather import Weather
from world.grid import SpatialGrid
from world.detritus import Detritus

from .stats import StatsTracker


class Simulation:
    def __init__(self):
        self.width = config.SIM_WIDTH
        self.height = config.SIM_HEIGHT

        self.environment = Environment()
        self.environment.regenerate_terrain()
        self.weather = Weather()

        self.plants: list[Plant] = []
        self.herbivores: list[Herbivore] = []
        self.carnivores: list[Carnivore] = []
        self.decomposers: list[Decomposer] = []
        self.detritus: list[Detritus] = []

        self.plant_grid = SpatialGrid(self.width, self.height, cell_size=40)
        self.herb_grid = SpatialGrid(self.width, self.height, cell_size=50)
        self.carn_grid = SpatialGrid(self.width, self.height, cell_size=60)
        self.decomposer_grid = SpatialGrid(self.width, self.height, cell_size=40)
        self.detritus_grid = SpatialGrid(self.width, self.height, cell_size=40)

        self.tick_count = 0.0
        self.stats = StatsTracker()

        self.selected_entity = None

        # a program mar egy legenaralt domborzattal, de nepesseg nelkul
        # indul (szerkeszto mod): a felhasznalo ujra generalhatja a
        # domborzatot, majd elhelyezi (kezzel vagy automatikusan) az
        # egyedeket, es a `start()` hivasaig az ido sem telik
        self.started = False

    # ------------------------------------------------------------------ #
    # Domborzat / népesítés / spawnolás
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        self.started = True

    def regenerate_terrain(self) -> None:
        self.environment.regenerate_terrain()

    _SPECIES_TABLE = {
        "plant": ("plants", config.MAX_PLANTS),
        "herbivore": ("herbivores", config.MAX_HERBIVORES),
        "carnivore": ("carnivores", config.MAX_CARNIVORES),
        "decomposer": ("decomposers", config.MAX_DECOMPOSERS),
    }
    _SPECIES_CLASSES = {
        "plant": Plant, "herbivore": Herbivore, "carnivore": Carnivore, "decomposer": Decomposer,
    }

    def populate_species_random(self, species: str, count: int) -> None:
        """Adott fajból `count` darabot helyez el véletlenszerűen a
        térképen (a manuális "+ ... lehelyezese" gombok automatikus
        párja), a faj populáció-korlátjáig."""
        species = species.lower()
        if species not in self._SPECIES_TABLE:
            return
        attr, cap = self._SPECIES_TABLE[species]
        cls = self._SPECIES_CLASSES[species]
        container = getattr(self, attr)
        for _ in range(count):
            if len(container) >= cap:
                break
            container.append(self._make_random(cls))

    def populate_all_random(self) -> None:
        self.populate_species_random("plant", config.INITIAL_PLANTS)
        self.populate_species_random("herbivore", config.INITIAL_HERBIVORES)
        self.populate_species_random("carnivore", config.INITIAL_CARNIVORES)
        self.populate_species_random("decomposer", config.INITIAL_DECOMPOSERS)

    def _make_random(self, cls, x: float | None = None, y: float | None = None):
        if x is None:
            x = random.uniform(0, self.width)
        if y is None:
            y = random.uniform(0, self.height)
        x, y = self._nearest_free_position(x, y, allow_water=cls.ALLOW_WATER_PLACEMENT)
        genome = Genome.random(cls.GENES)
        return cls(x, y, genome)

    def _nearest_free_position(self, x: float, y: float, allow_water: bool = False) -> tuple[float, float]:
        """Ha (x, y) akadályba (vagy - ha `allow_water` hamis - állóvízbe)
        esne, a legközelebbi szabad cellát keresi egyre táguló gyűrűkben,
        hogy egyedek soha ne ragadjanak akadályba. Növényeknél (`allow_water`)
        csak a sziklákat kerüljük, mert víztűrő genommal vízben is
        megélhetnek."""
        is_blocked = self.environment.is_obstacle if allow_water else self.environment.is_blocked
        if not is_blocked(x, y):
            return x, y
        cell = config.CELL_SIZE
        for radius in range(1, 10):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx = min(max(x + dx * cell, 0), self.width)
                    ny = min(max(y + dy * cell, 0), self.height)
                    if not is_blocked(nx, ny):
                        return nx, ny
        return x, y

    def spawn_entity(self, species: str, x: float, y: float) -> None:
        species = species.lower()
        if species == "plant" and len(self.plants) < config.MAX_PLANTS:
            self.plants.append(self._make_random(Plant, x, y))
        elif species == "herbivore" and len(self.herbivores) < config.MAX_HERBIVORES:
            self.herbivores.append(self._make_random(Herbivore, x, y))
        elif species == "carnivore" and len(self.carnivores) < config.MAX_CARNIVORES:
            self.carnivores.append(self._make_random(Carnivore, x, y))
        elif species == "decomposer" and len(self.decomposers) < config.MAX_DECOMPOSERS:
            self.decomposers.append(self._make_random(Decomposer, x, y))

    def reproduce_plants(self, a: Plant, b: Plant) -> None:
        """Ket kozeli noveny ivaros szaporodasa: a gyermek genomja
        mindket szulotol szarmazik (crossover), a szulok sajat mutacios
        hajlamuk atlaga alapjan mutalodva (lasd `reproduce_mobile`)."""
        if len(self.plants) >= config.MAX_PLANTS:
            return
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(6.0, max(a.traits["seed_spread"], b.traits["seed_spread"]))
        mx, my = (a.x + b.x) / 2.0, (a.y + b.y) / 2.0
        x = min(max(mx + math.cos(angle) * dist, 0), self.width)
        y = min(max(my + math.sin(angle) * dist, 0), self.height)
        if self.environment.is_obstacle(x, y):
            return
        rate = (a.traits["mutation_rate"] + b.traits["mutation_rate"]) / 2.0
        strength = (a.traits["mutation_strength"] + b.traits["mutation_strength"]) / 2.0
        genome = a.genome.crossover(b.genome).mutate(rate, strength)
        child = Plant(x, y, genome, generation=max(a.generation, b.generation) + 1, is_seed=True)
        self.plants.append(child)

    def reproduce_mobile(self, a, b, container: list, cap: int) -> None:
        if len(container) >= cap:
            return
        # ket szulonel a mutacios hajlamuk atlaga hatarozza meg, mennyire
        # mutalodjon a gyermek genomja (lasd `reproduce_plants`)
        rate = (a.traits["mutation_rate"] + b.traits["mutation_rate"]) / 2.0
        strength = (a.traits["mutation_strength"] + b.traits["mutation_strength"]) / 2.0
        child_genome = a.genome.crossover(b.genome).mutate(rate, strength)
        cx = min(max((a.x + b.x) / 2 + random.uniform(-8, 8), 0), self.width)
        cy = min(max((a.y + b.y) / 2 + random.uniform(-8, 8), 0), self.height)
        cx, cy = self._nearest_free_position(cx, cy)
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

    def find_plant_food(self, entity, max_range: float):
        """A `find_nearest` novenyekre specializalt valtozata: a meg ki nem
        hajtott magvakat es a mar elbomlo tetemeket (lasd Plant `is_seed`/
        `corpse`) nem szamitja taplaleknak, mert azok energiatartalma
        elhanyagolhato/nulla - a novenyevok csak a mar kifejlett,
        fotoszintetizalo novenyeket keresik."""
        best, best_dist = None, max_range
        for candidate in self.plant_grid.query_radius(entity.x, entity.y, max_range):
            if not candidate.alive or candidate.is_seed or candidate.corpse:
                continue
            dist = entity.distance_to(candidate)
            if dist < best_dist:
                best_dist = dist
                best = candidate
        return best

    def find_plant_mate(self, entity: Plant):
        """A novenynek nincs "latotere" (helyhez kotott), ezert a sajat
        `seed_spread` genje (mag-/pollenszoras tavolsaga) hatarozza meg,
        milyen tavoli masik novennyel szaporodhat - csak akkor, ha az is
        kesz a szaporodasra (nincs hutesi ideje, eleg energiaja van)."""
        radius = entity.traits["seed_spread"]
        best, best_dist = None, radius
        for candidate in self.plant_grid.query_radius(entity.x, entity.y, radius):
            if candidate is entity or not candidate.alive:
                continue
            if candidate.reproduce_cooldown > 0:
                continue
            if candidate.energy < candidate.max_energy * 0.75:
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
        if not self.started or self.weather.paused:
            return
        dt = real_dt_frames * self.weather.time_scale
        self._step(dt)

    def step_once(self) -> None:
        self._step(1.0)

    def _step(self, dt: float) -> None:
        # az elozo tickben elhunyt (es mar egy teljes tickig "Halott"
        # allapotban megfigyelheto) egyedeket most tavolitjuk el vegleg
        self._purge_dead()

        self.tick_count += dt
        self.weather.update(dt)
        self.environment.update(dt, self.weather)

        self.plant_grid.build(self.plants)
        self.herb_grid.build(self.herbivores)
        self.carn_grid.build(self.carnivores)
        self.decomposer_grid.build(self.decomposers)
        self.detritus_grid.build(self.detritus)

        for plant in self.plants:
            plant.update(dt, self)
        for herbivore in self.herbivores:
            herbivore.update(dt, self)
        for carnivore in self.carnivores:
            carnivore.update(dt, self)
        for decomposer in self.decomposers:
            decomposer.update(dt, self)

        self._mark_newly_dead()
        self.stats.record(self)

    def _spawn_detritus(self, entity) -> None:
        """Elpusztult entitás testtömegének egy részét "detritusszá" alakítja,
        amit a lebontók humusszá bonthatnak."""
        amount = entity.max_energy * entity.CORPSE_RATIO
        if amount > 0.5:
            self.detritus.append(Detritus(entity.x, entity.y, amount))

    def _mark_newly_dead(self) -> None:
        """Az ebben a tickben elhunyt egyedeket "Halott" allapotba allitja es
        detritust hoz letre beloluk, de meg NEM tavolitja el oket - igy egy
        teljes tickig megfigyelhetok/kivalaszthatok maradnak, mielott a
        kovetkezo `_purge_dead()` tenylegesen kiveszi oket a listakbol."""
        for group in (self.plants, self.herbivores, self.carnivores, self.decomposers):
            for entity in group:
                if entity.is_dead() and not entity.pending_removal:
                    entity.pending_removal = True
                    entity.state = states.DEAD
                    # a novenyi tetem (lasd Plant._update_corpse) mar
                    # fokozatosan, a homerseklet szerint elbomlott, ezert
                    # nem termel meg kulon Detritus-t is - csak az allati
                    # tetemek kerulnek a lebontok altal evett kupacba
                    if not isinstance(entity, Plant):
                        self._spawn_detritus(entity)

    def _purge_dead(self) -> None:
        if self.selected_entity is not None and getattr(self.selected_entity, "pending_removal", False):
            self.selected_entity = None
        self.plants = [e for e in self.plants if not e.pending_removal]
        self.herbivores = [e for e in self.herbivores if not e.pending_removal]
        self.carnivores = [e for e in self.carnivores if not e.pending_removal]
        self.decomposers = [e for e in self.decomposers if not e.pending_removal]
        self.detritus = [d for d in self.detritus if d.alive]

    def reset(self) -> None:
        self.__init__()
