"""Növény: helyhez kötött, fotoszintézissel táplálkozó entitás."""

from __future__ import annotations

import math
import random

import config
from . import states
from .base import Entity
from .genome import Genome


class Plant(Entity):
    GENES = config.PLANT_GENES
    RANGES = config.PLANT_RANGES
    BASE_COLOR = config.COLOR_PLANT
    CORPSE_RATIO = config.PLANT_CORPSE_RATIO
    # a novenyeket a `water_tolerance` genjuk donti el, hogy megelnek-e
    # allovízben - ezert (a tobbi fajtol elteroen) nem kerulik a to/tenger
    # celakat mar a lehelyezeskor/magszorasnal sem (lasd Simulation)
    ALLOW_WATER_PLACEMENT = True

    def __init__(
        self,
        x: float,
        y: float,
        genome: Genome,
        energy: float | None = None,
        generation: int = 0,
        is_seed: bool = False,
    ):
        super().__init__(x, y, genome, energy=energy, generation=generation)
        # szaporodaskor (lasd Simulation.reproduce_plants) a gyermek magkent
        # jon letre: kis energiatartalekkal, es csak akkor kezd el noni,
        # ha a helyi homerseklet/viz/humusz megfelel a DNS-ben rogzitett
        # igenyeinek (lasd `_update_seed`) - kezzel lehelyezett/kezdeti
        # novenyek viszont mar kifejlett noveny(ke)kent jonnek letre
        self.is_seed = is_seed
        if is_seed:
            self.energy = self.max_energy * config.PLANT_SEED_ENERGY_RATIO
            self.state = states.SEED
        # elpusztulas utan (kicsirazatlan mag vagy kifejlett noveny) a
        # noveny nem tunik el azonnal: "tetemme" valik, ami fokozatosan,
        # a homerseklettol fuggo utemben fogy el (lasd `_update_corpse`)
        self.corpse = False
        self.corpse_mass = 0.0
        self.corpse_mass_initial = 0.0

    def is_dead(self) -> bool:
        # a novenyt csak akkor tavolitja el a szimulacio, ha mar teljesen
        # elbomlott tetemme valt - az energia-kifogyas/eletkor tuli kort
        # maga a `update` eszleli es alakitja at tetemme (lasd lent)
        if self.corpse:
            return self.corpse_mass <= 0.0
        return False

    @property
    def current_height(self) -> float:
        """A `max_height` gen adja a noveny vegso, kifejlett meretet - az
        aktualis (meg noveksben levo) magassag ehhez kepest az energia-
        arannyal aranyos, ugy ahogy a rajzolt sugar is (lasd `draw`)."""
        return self.traits.get("max_height", 6.0) * self.energy_ratio

    def _shade_factor(self, sim) -> float:
        """Megkeresi a legkozelebbi, nala erdemben magasabbra novo
        szomszedot (a `plant_grid`-ben), es az annak lombja altal vetett
        arnyek merteket adja vissza (0 = nincs arnyek, `PLANT_SHADE_MAX_FACTOR`
        = teljesen elarnyekolva). A sajat magassagat meghalado szomszedok
        kozul a legerosebb arnyekolo hatas szamit, nem osszeadodnak."""
        own_height = self.current_height
        max_possible_radius = self.RANGES["max_height"][1] * config.PLANT_SHADE_RADIUS_FACTOR
        strongest_shade = 0.0
        for neighbor in sim.plant_grid.query_radius(self.x, self.y, max_possible_radius):
            if neighbor is self or not neighbor.alive:
                continue
            neighbor_height = neighbor.current_height
            if neighbor_height <= own_height:
                continue
            shade_radius = neighbor_height * config.PLANT_SHADE_RADIUS_FACTOR
            dist = self.distance_to(neighbor)
            if dist >= shade_radius:
                continue
            closeness = 1.0 - dist / shade_radius
            height_diff = (neighbor_height - own_height) / neighbor_height
            shade = config.PLANT_SHADE_MAX_FACTOR * closeness * height_diff
            strongest_shade = max(strongest_shade, shade)
        return strongest_shade

    def _become_corpse(self) -> None:
        self.corpse = True
        self.corpse_mass_initial = self.max_energy * self.CORPSE_RATIO
        self.corpse_mass = self.corpse_mass_initial
        self.energy = 0.0
        self.state = states.DEAD

    def _update_corpse(self, dt: float, sim) -> None:
        """A tetem (elpusztult mag vagy kifejlett noveny) fokozatosan
        elfogy: a bomlas utemet a helyi homerseklet szabja - melegben
        gyorsabban, hidegben lassabban rothad el, mint a `Detritus`/
        lebontok altal evett allati tetemek, ezert nem is termel kulon
        `Detritus`-t (lasd Simulation._mark_newly_dead). Az elfogyo tomeg
        egy resze kozvetlenul humusszá valik a tetem helyen - a novenyi
        anyag igy lebonto szervezetek nelkul is visszakerul a talajba."""
        self.age += dt
        env = sim.environment
        temp = env.get_temperature(self.x, self.y)
        temp_mult = 1.0 + config.PLANT_CORPSE_DECAY_TEMP_COEFF * (temp - config.PLANT_CORPSE_DECAY_TEMP_REF)
        temp_mult = min(config.PLANT_CORPSE_DECAY_MAX_MULT, max(config.PLANT_CORPSE_DECAY_MIN_MULT, temp_mult))
        decay = config.PLANT_CORPSE_DECAY_BASE_RATE * temp_mult * dt
        mass_lost = min(self.corpse_mass, self.corpse_mass_initial * decay)
        self.corpse_mass -= mass_lost
        if mass_lost > 0.0:
            env.add_humus(self.x, self.y, mass_lost * config.PLANT_CORPSE_HUMUS_YIELD)
        self.state = states.DEAD

    def _update_seed(self, dt: float, sim) -> None:
        """Amig mag allapotban van, nem fotoszintetizal/no - csak figyeli,
        hogy a helyi homerseklet (a mar meglevo `temp_min`/`temp_max` gen
        szerint) es a viz/humuszszint (a sajat `germination_water`/
        `germination_humus` genje szerint) megfelel-e a kicsirazashoz. Ha
        sokaig (`seed_viability` gen) nem talalkozik ilyen korulmennyel,
        a mag elpusztul (tetemme valik)."""
        self.age += dt
        env = sim.environment
        temp = env.get_temperature(self.x, self.y)
        water = env.get_water(self.x, self.y)
        humus = env.get_humus(self.x, self.y)

        t_min, t_max = self.traits["temp_min"], self.traits["temp_max"]
        temp_ok = t_min <= temp <= t_max
        water_ok = water >= self.traits["germination_water"]
        humus_ok = humus >= self.traits["germination_humus"]

        if temp_ok and water_ok and humus_ok:
            self.is_seed = False
            self.age = 0.0
            self.state = states.GROWING
            return

        self.state = states.SEED
        if self.age > self.traits["seed_viability"]:
            self._become_corpse()

    def update(self, dt: float, sim) -> None:
        if self.corpse:
            self._update_corpse(dt, sim)
            return
        if self.is_seed:
            self._update_seed(dt, sim)
            return

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

        # tul sok/allando viz (pl. to/tenger fenek): a `water_tolerance` gén
        # szabja meg, mennyire bírja - alacsony tolerancia esetén visszaesik
        # a növekedés, súlyos és tartós elárasztásnál pedig el is korhad;
        # magas tolerancia (vízinövény) esetén a flood_stress ~0, tehát
        # korlátlanul megél állóvízben is
        water_tolerance = self.traits["water_tolerance"]
        flood_excess = max(0.0, water - water_need - config.PLANT_FLOOD_MARGIN)
        flood_stress = flood_excess * (1.0 - water_tolerance)

        humus = env.get_humus(self.x, self.y)
        humus_bonus = 1.0 + min(1.0, humus) * config.HUMUS_GROWTH_BONUS

        # a kozeli, nala nagyobbra novo novenyek (`max_height` gen) beeloznek
        # a fenybol: minel nagyobb es minel kozelebbi az arnyekolo szomszed,
        # annal tobbet von le a sajat fotoszintezisehez juto fenybol
        sun *= 1.0 - self._shade_factor(sim)

        # az energiatermeles (fotoszintezis) a novenyre juto tenyleges
        # fenytol (`sun`, ami mar figyelembe veszi a napszakot/esot/arnyekot)
        # ES a level zoldjenek melysegetol (`chlorophyll` gen) fugg: minel
        # melyebb zold, annal hatekonyabban hasznositja a fenyt
        light_factor = 0.2 + 0.8 * sun
        chlorophyll_factor = 0.5 + 0.5 * self.traits["chlorophyll"]
        photosynthesis = light_factor * chlorophyll_factor

        growth = self.traits["growth_rate"] * temp_factor * water_factor * photosynthesis * humus_bonus * dt
        growth *= max(0.0, 1.0 - flood_stress)
        self.energy = min(self.max_energy, self.energy + growth * self.max_energy)
        self.state = states.GROWING

        # elhervadás szélsőséges hőmérsékletben / tartós vízhiányban / tartós
        # elárasztásban (utóbbi a súlyosság szerint arányosan gyorsabban öl)
        stress = 0.0
        if temp_factor <= 0.03:
            stress = 1.0
        if water < water_need * 0.2 and drought_resistance < 0.25:
            stress = 1.0
        if flood_stress > 0.4:
            stress = max(stress, min(1.0, flood_stress))
        if stress > 0.0:
            self.energy -= 0.5 * dt * self.max_energy * 0.05 * stress
            self.state = states.WITHERING

        self.reproduce_cooldown -= dt
        if self.energy > self.max_energy * 0.75 and self.reproduce_cooldown <= 0:
            # csak akkor szaporodik, ha van egy kozeli (pollenszorason
            # beluli), szinten szaporodasra kesz masik noveny - a gyermek
            # genomja mindket szulotol szarmazik (crossover + mutacio)
            mate = sim.find_plant_mate(self)
            if mate is not None:
                sim.reproduce_plants(self, mate)
                self.energy *= 0.55
                mate.energy *= 0.55
                cooldown = 140.0 + random.uniform(0.0, 120.0)
                self.reproduce_cooldown = cooldown
                mate.reproduce_cooldown = cooldown
                self.state = states.SEEDING
                mate.state = states.SEEDING

        if self.energy <= 0.0 or self.age > self.traits["lifespan"]:
            self._become_corpse()

    def draw(self, surface) -> None:
        import pygame

        pos = (int(self.x), int(self.y))
        if self.corpse:
            # a tetem a hattralevo tomegevel (`corpse_mass`) aranyosan
            # zsugorodik, ahogy fokozatosan elbomlik
            ratio = self.corpse_mass / self.corpse_mass_initial if self.corpse_mass_initial > 0 else 0.0
            radius = 1 + int(ratio * 3)
            pygame.draw.circle(surface, (100, 85, 65), pos, max(1, radius))
            return
        if self.is_seed:
            # kicsi, barnas pont - meg nem hajtott ki
            pygame.draw.circle(surface, (150, 115, 55), pos, 2)
            return

        ratio = self.energy_ratio
        max_height = self.traits.get("max_height", 6.0)
        radius = 2 + int(ratio * (1.0 + max_height * 0.4))
        r, g, b = self.BASE_COLOR
        # a level zoldjenek arnyalatat a `chlorophyll` gen adja: vilagos,
        # sargas-zoldtol (alacsony gen) a melyzoldig (magas gen)
        chlorophyll = self.traits.get("chlorophyll", 0.5)
        r = r * (1.3 - 0.6 * chlorophyll)
        g = g * (0.7 + 0.5 * chlorophyll)
        b = b * (0.6 + 0.6 * chlorophyll)
        color = (int(r * (0.4 + 0.6 * ratio)), int(g * (0.5 + 0.5 * ratio)), int(b * (0.4 + 0.6 * ratio)))
        # viztures kepesseg szerinti tonus: szarazsagkedvelo -> sargas-barna,
        # vizinoveny -> kekes-zold, hogy a kialakulo tipusok jol lathatok legyenek
        wt = self.traits.get("water_tolerance", 0.5)
        if wt < 0.5:
            dryness = (0.5 - wt) * 2.0
            color = (min(255, int(color[0] + dryness * 60)), color[1], int(color[2] * (1.0 - dryness * 0.5)))
        elif wt > 0.5:
            wetness = (wt - 0.5) * 2.0
            color = (int(color[0] * (1.0 - wetness * 0.4)), color[1], min(255, int(color[2] + wetness * 90)))
        if self.state == states.WITHERING:
            color = (min(255, int(color[0] + 40)), int(color[1] * 0.6), int(color[2] * 0.5))
        pygame.draw.circle(surface, color, pos, radius)
