"""Rács alapú környezeti mezők: hőmérséklet, víz és terepakadályok, NumPy-val."""

from __future__ import annotations

import random

import numpy as np

import config


class Environment:
    def __init__(self, cols: int = config.WORLD_COLS, rows: int = config.WORLD_ROWS, cell_size: int = config.CELL_SIZE):
        self.cols = cols
        self.rows = rows
        self.cell_size = cell_size
        self.temperature = np.full((rows, cols), config.DEFAULT_BASE_TEMP, dtype=np.float64)
        self.water = np.random.uniform(0.25, 0.55, size=(rows, cols))
        self.humus = np.zeros((rows, cols), dtype=np.float64)

        self.temp_gradient_per_100m = config.DEFAULT_TEMP_GRADIENT_PER_100M
        self.elevation_min_meters = config.ELEVATION_MIN_METERS
        self.elevation_max_meters = config.ELEVATION_MAX_METERS
        self.water_level_meters = config.DEFAULT_WATER_LEVEL_METERS
        self.water_level_threshold = 0.0

        # alapertelmezetten lapos domborzat (nincs hegy/szikla/allovíz);
        # a Simulation induláskor rögtön meghívja a `regenerate_terrain`-t,
        # a felhasználó pedig a "Domborzat ujragenerálása" gombbal bármikor
        # ujra lecserélheti
        self.obstacles = np.zeros((rows, cols), dtype=bool)
        self.elevation = np.zeros((rows, cols), dtype=np.float64)
        self.is_water = np.zeros((rows, cols), dtype=bool)
        self.blocked = np.zeros((rows, cols), dtype=bool)
        self.pressure = np.full((rows, cols), config.DEFAULT_SEA_LEVEL_PRESSURE, dtype=np.float64)
        self._flow_accumulation = np.ones((rows, cols), dtype=np.float64)
        self.stream_mask = np.zeros((rows, cols), dtype=bool)
        self.stream_intensity = np.zeros((rows, cols), dtype=np.float64)
        self.slope = np.zeros((rows, cols), dtype=np.float64)
        self._flow_down_dr = np.zeros((rows, cols), dtype=np.int8)
        self._flow_down_dc = np.zeros((rows, cols), dtype=np.int8)
        self._flow_has_outflow = np.zeros((rows, cols), dtype=bool)
        row_idx, col_idx = np.indices((rows, cols))
        self._flow_target_row = row_idx.copy()
        self._flow_target_col = col_idx.copy()

    def regenerate_terrain(self) -> None:
        """Újragenerálja a domborzatot (magasságtérkép, sziklák, ebből
        következő állóvizek) - bármikor meghívható, pl. a szerkesztő
        módban egy "Domborzat ujragenerálása" gombbal."""
        self.obstacles = self._generate_obstacles()
        self.elevation = self._generate_elevation()
        self._recompute_water_mask()
        self._compute_flow_routing()
        self._apply_initial_steep_drainage()
        self._flow_accumulation = self._compute_flow_accumulation()
        self._recompute_streams()
        self._recompute_pressure()
        self._recompute_initial_temperature()
        self._recompute_initial_humus()

    def _compute_flow_routing(self) -> None:
        """D8-szeru lejto-irany: minden cellahoz megkeresi a korulotte levo
        8 szomszed kozul a legalacsonyabbikat (ha van nala alacsonyabb),
        es ezt hasznalja mind a lefolyas-halmozodashoz (`_compute_flow_
        accumulation`), mind a meredek-lejtos vizlefolyashoz (lasd
        `update`). A `slope` (0-1) azt mutatja, mennyivel meredekebb egy
        cella a tobbihez kepest (a lejto-iranyu szomszedhoz kepesti szint-
        kulonbseg alapjan) - ez alapjan folyik le onnan a viz a
        legmeredekebb helyeken."""
        rows, cols = self.elevation.shape
        elev = self.elevation
        padded = np.pad(elev, 1, mode="constant", constant_values=np.inf)
        best_elev = elev.copy()
        down_dr = np.zeros((rows, cols), dtype=np.int8)
        down_dc = np.zeros((rows, cols), dtype=np.int8)
        has_outflow = np.zeros((rows, cols), dtype=bool)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                neighbor = padded[1 + dr: 1 + dr + rows, 1 + dc: 1 + dc + cols]
                better = neighbor < best_elev
                best_elev = np.where(better, neighbor, best_elev)
                down_dr = np.where(better, dr, down_dr)
                down_dc = np.where(better, dc, down_dc)
                has_outflow |= better

        self._flow_down_dr = down_dr
        self._flow_down_dc = down_dc
        self._flow_has_outflow = has_outflow
        row_idx, col_idx = np.indices((rows, cols))
        self._flow_target_row = np.clip(row_idx + down_dr, 0, rows - 1)
        self._flow_target_col = np.clip(col_idx + down_dc, 0, cols - 1)

        drop = np.where(has_outflow, elev - best_elev, 0.0)
        max_drop = float(drop.max())
        self.slope = drop / max_drop if max_drop > 1e-9 else np.zeros_like(drop)

    def _apply_initial_steep_drainage(self) -> None:
        """A meredek domborzatu cellak kezdeti viztartalmat is azonnal
        csokkenti - enelkul a hatas (lasd `update`) csak futo szimulacio
        soran, fokozatosan jelenne meg, a szerkeszto modban meg nem
        latszana a meredek lejtokon a vizhiany."""
        steepness = np.clip(
            (self.slope - config.STEEP_RUNOFF_THRESHOLD) / max(1e-6, 1.0 - config.STEEP_RUNOFF_THRESHOLD), 0.0, 1.0
        )
        self.water *= (1.0 - steepness * 0.6)

    def _compute_flow_accumulation(self) -> np.ndarray:
        """A `_compute_flow_routing`-ban meghatarozott lejto-iranyok alapjan:
        a legmagasabb cellaktol a legalacsonyabbak fele haladva minden
        cella hozzaadja a sajat (mar felhalmozott) vizmennyiseget a lejto
        iranyaban levo szomszedjahoz, igy mire egy cellahoz erunk, minden
        "felvizi" hozzajarulasa mar benne van a sajat ertekeben. Az igy
        kapott ertek ott nagy, ahol sok felvizi cellarol folyik ossze a
        viz - ezekbol lesznek a patakok, a volgyekben osszefutva."""
        rows, cols = self.elevation.shape
        order = np.argsort(self.elevation, axis=None)[::-1]
        rows_idx, cols_idx = np.unravel_index(order, self.elevation.shape)
        accumulation = np.ones((rows, cols), dtype=np.float64)
        down_dr, down_dc, has_outflow = self._flow_down_dr, self._flow_down_dc, self._flow_has_outflow
        for r, c in zip(rows_idx.tolist(), cols_idx.tolist()):
            if has_outflow[r, c]:
                tr = r + int(down_dr[r, c])
                tc = c + int(down_dc[r, c])
                accumulation[tr, tc] += accumulation[r, c]
        return accumulation

    def _recompute_streams(self) -> None:
        """A lefolyas-halmozodasbol (`_flow_accumulation`) kijeloli a
        patak-cellakat: azokat a szarazfoldi cellakat, ahol elegendo
        felvizi terulet vize folyik at ahhoz, hogy lathato eret alkosson.
        Az `stream_intensity` (0-1) minel nagyobb, annal tobb viz folyik
        ott ossze - ez hatarozza meg a patak lathato "vizesseget" is."""
        accumulation = self._flow_accumulation
        land = ~self.is_water & ~self.obstacles
        self.stream_mask = np.zeros_like(land)
        self.stream_intensity = np.zeros_like(accumulation)
        if not land.any():
            return
        threshold = max(float(np.percentile(accumulation[land], config.STREAM_ACCUMULATION_PERCENTILE)), 2.0)
        mask = land & (accumulation >= threshold)
        if not mask.any():
            return
        span = max(1e-6, float(accumulation[mask].max()) - threshold)
        self.stream_mask = mask
        self.stream_intensity[mask] = np.clip((accumulation[mask] - threshold) / span, 0.0, 1.0)
        # a patakokat azonnal (a szerkeszto modban is) lathato vizszintre
        # toltjuk, hogy ne csak futo szimulacio kozben tunjenek fel (lasd
        # meg az `update`-ben levo, folyamatos utantoltest)
        stream_target = np.zeros_like(self.water)
        stream_target[mask] = 0.35 + 0.6 * self.stream_intensity[mask]
        self.water = np.maximum(self.water, stream_target)

    def _recompute_initial_temperature(self) -> None:
        """A homerseklet mezot azonnal a magassag-gradiensnek megfelelo
        egyensulyi ertekre allitja - enelkul a `update()` (ami csak
        elindult, futo szimulacio eseten fut le) nelkul a szerkeszto
        modban meg lapos, egyenletes maradna a homerseklet terkep, es nem
        latszana rajta a magassagbol adodo kulonbseg."""
        meters = self.elevation_to_meters(self.elevation)
        self.temperature = config.DEFAULT_BASE_TEMP - meters / 100.0 * self.temp_gradient_per_100m

    def _snow_line_meters(self) -> float:
        """Az a magassag (m), ahol a kezdeti homerseklet mar 0 fok ala esik
        (lasd `_recompute_initial_temperature`) - ez szamit "havas" hatarnak
        a kezdeti humusz-eloszlashoz."""
        if self.temp_gradient_per_100m > 1e-9:
            return config.DEFAULT_BASE_TEMP * 100.0 / self.temp_gradient_per_100m
        return self.elevation_max_meters

    def _recompute_initial_humus(self) -> None:
        """Kezdeti humusz-eloszlas a magassag fuggvenyeben: a 0 magassagon
        (tengerszinten) es az alatt a legtobb, a hohatarnal (lasd
        `_snow_line_meters`) mar 0, a ketto kozott pedig linearisan
        csokken."""
        meters = self.elevation_to_meters(self.elevation)
        snow_line = max(self._snow_line_meters(), 1e-6)
        frac = 1.0 - np.clip(meters, 0.0, snow_line) / snow_line
        self.humus = config.HUMUS_MAX * np.clip(frac, 0.0, 1.0)

    def set_temp_gradient_per_100m(self, value: float) -> None:
        self.temp_gradient_per_100m = value
        self._recompute_initial_temperature()
        self._recompute_initial_humus()

    def elevation_to_meters(self, elevation_norm) -> np.ndarray | float:
        """A 0-1 tartományba normalizált `elevation` erteket alakitja at
        tenyleges meterekre, a beallitott minimum/maximum magassag alapjan."""
        span = self.elevation_max_meters - self.elevation_min_meters
        return self.elevation_min_meters + elevation_norm * span

    def meters_to_elevation_norm(self, meters: float) -> float:
        """Az `elevation_to_meters` inverze: egy tenyleges meter-erteket
        (pl. a beallitott vizszint vagy hohatar) alakit vissza a belsőleg
        hasznalt 0-1 normalizalt elevation-skalara."""
        span = self.elevation_max_meters - self.elevation_min_meters
        if span < 1e-9:
            return 0.0
        return (meters - self.elevation_min_meters) / span

    def set_elevation_range_meters(self, min_meters: float, max_meters: float) -> None:
        self.elevation_min_meters = min_meters
        self.elevation_max_meters = max_meters
        self._recompute_water_mask()
        self._recompute_pressure()
        self._recompute_initial_temperature()
        self._recompute_initial_humus()

    def set_water_level_meters(self, value: float) -> None:
        self.water_level_meters = value
        self._recompute_water_mask()
        self._recompute_streams()

    def _recompute_pressure(self) -> None:
        """A legnyomas kizarolag a magassagbol szamitodik, leegyszerusitett
        barometrikus kozelitessel: minel magasabban van egy cella, annal
        ritkabb (alacsonyabb nyomasu) a "levego" ott."""
        meters = self.elevation_to_meters(self.elevation)
        self.pressure = config.DEFAULT_SEA_LEVEL_PRESSURE - meters * config.PRESSURE_LAPSE_PER_METER

    def _generate_elevation(self) -> np.ndarray:
        """Diamond-square fraktál-algoritmussal generál magasságtérképet:
        a négyzet sarkaiból indulva felezgeti a rácsot, minden felezésnél
        a négy szomszéd átlagához egyre kisebb véletlen eltérést adva. Ez
        - a durva rács-felnagyítás+elsimítással szemben - egyszerre ad
        nagy hegyvonulatokat és apró, dombormű-szerű részleteket, külön
        zaj-könyvtár nélkül."""
        size = max(self.rows, self.cols)
        power = max(1, (size - 1).bit_length())
        full_size = 2 ** power + 1
        grid = self._diamond_square(full_size, config.ELEVATION_ROUGHNESS)
        elevation = grid[: self.rows, : self.cols]
        lo, hi = elevation.min(), elevation.max()
        if hi - lo > 1e-6:
            elevation = (elevation - lo) / (hi - lo)
        return elevation

    @staticmethod
    def _diamond_square(full_size: int, roughness: float) -> np.ndarray:
        """A klasszikus diamond-square algoritmus egy `full_size` x
        `full_size` (2^n + 1 méretű) rácson. `roughness` (0-1) szabja meg,
        hogy a véletlen eltérés mértéke milyen gyorsan csökken finomodó
        lépésközönként: alacsony érték sima dombokat, magas érték
        szaggatott, sziklás terepet ad."""
        grid = np.zeros((full_size, full_size), dtype=np.float64)
        grid[0, 0] = random.uniform(0.0, 1.0)
        grid[0, -1] = random.uniform(0.0, 1.0)
        grid[-1, 0] = random.uniform(0.0, 1.0)
        grid[-1, -1] = random.uniform(0.0, 1.0)

        step = full_size - 1
        scale = 1.0
        while step > 1:
            half = step // 2

            # diamond lepes: a negyzetek kozeppontjat a negy sarok
            # atlagabol + veletlen eltolassal hatarozza meg
            for y in range(half, full_size, step):
                for x in range(half, full_size, step):
                    avg = (
                        grid[y - half, x - half]
                        + grid[y - half, x + half]
                        + grid[y + half, x - half]
                        + grid[y + half, x + half]
                    ) / 4.0
                    grid[y, x] = avg + random.uniform(-1.0, 1.0) * scale

            # square lepes: a rombuszok kozeppontjat a (racsontuli
            # szomszedokat kihagyva) elerheto szomszedok atlagabol
            # hatarozza meg
            for y in range(0, full_size, half):
                x_start = half if y % step == 0 else 0
                for x in range(x_start, full_size, step):
                    total = 0.0
                    count = 0
                    if y - half >= 0:
                        total += grid[y - half, x]
                        count += 1
                    if y + half < full_size:
                        total += grid[y + half, x]
                        count += 1
                    if x - half >= 0:
                        total += grid[y, x - half]
                        count += 1
                    if x + half < full_size:
                        total += grid[y, x + half]
                        count += 1
                    grid[y, x] = total / count + random.uniform(-1.0, 1.0) * scale

            step = half
            scale *= roughness

        return grid

    def _recompute_water_mask(self) -> None:
        """A `water_level_meters` (a beallitott min/max magassaghoz kepest
        atszamitva) alapján kijelöli a mély, állandóan víz alatti cellákat
        (tavak/tenger), és ezeket a sziklás akadályokkal együtt
        "járhatatlanná" teszi."""
        self.water_level_threshold = np.clip(self.meters_to_elevation_norm(self.water_level_meters), 0.0, 1.0)
        self.is_water = self.elevation < self.water_level_threshold
        self.blocked = self.obstacles | self.is_water
        self.water[self.is_water] = config.LAKE_WATER_LEVEL

    def _generate_obstacles(self) -> np.ndarray:
        """Sziklatömböket rajzol véletlen sétával, hogy szerves alakú,
        összefüggő akadályok jöjjenek létre szórt egyedi cellák helyett."""
        obstacles = np.zeros((self.rows, self.cols), dtype=bool)
        steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for _ in range(config.OBSTACLE_CLUSTER_COUNT):
            row = random.randint(0, self.rows - 1)
            col = random.randint(0, self.cols - 1)
            length = random.randint(*config.OBSTACLE_CLUSTER_SIZE)
            for _ in range(length):
                obstacles[row, col] = True
                dr, dc = random.choice(steps)
                row = min(max(row + dr, 0), self.rows - 1)
                col = min(max(col + dc, 0), self.cols - 1)
        return obstacles

    def _diffuse(self, field: np.ndarray, rate: float) -> None:
        neighbor_avg = (
            np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0)
            + np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
        ) / 4.0
        field += (neighbor_avg - field) * rate

    def update(self, dt: float, weather) -> None:
        sun = weather.sunlight_factor()
        base_target = weather.base_temperature + (sun - 0.5) * 14.0
        if weather.raining:
            base_target -= 3.0
        # a magasabban fekvő ("domborzat") cellák hidegebbek: a 0 magassaghoz (tengerszint)
        # kepesti meterek alapjan, a beallitott gradienssel (fok/100m) hulnek/melegednek
        elevation_meters = self.elevation_to_meters(self.elevation)
        target_field = base_target - elevation_meters / 100.0 * self.temp_gradient_per_100m
        self.temperature += (target_field - self.temperature) * min(1.0, 0.01 * dt)
        self._diffuse(self.temperature, 0.04)

        if weather.raining:
            self.water += weather.rain_intensity * dt * 0.01

        evaporation = 0.0015 * dt * (1.0 + np.clip((self.temperature - 20.0) / 20.0, 0.0, None))
        self.water -= evaporation
        np.clip(self.water, 0.0, 1.0, out=self.water)
        self._diffuse(self.water, 0.06)

        # nagyon meredek domborzaton a viz nem marad ott: lefolyik a
        # lejto-iranyu szomszedjaba (lasd `_compute_flow_routing`), minel
        # meredekebb, annal tobb - igy a meredek lejtokon csokken, a
        # volgyekben/patakokban pedig gyarapszik
        steepness = np.clip(
            (self.slope - config.STEEP_RUNOFF_THRESHOLD) / max(1e-6, 1.0 - config.STEEP_RUNOFF_THRESHOLD), 0.0, 1.0
        )
        runoff = np.where(self._flow_has_outflow, self.water * steepness * config.STEEP_RUNOFF_RATE * dt, 0.0)
        self.water -= runoff
        np.add.at(self.water, (self._flow_target_row.ravel(), self._flow_target_col.ravel()), runoff.ravel())
        np.clip(self.water, 0.0, 1.0, out=self.water)

        # az állóvíz (tó/tenger) cellák állandó, ki nem apadó vízforrások,
        # amik diffúzióval a szomszédos szárazföldet is öntözik
        self.water[self.is_water] = config.LAKE_WATER_LEVEL
        # a patakok is folyamatosan utantoltodnek (a felvizi terulet
        # "esovize" allandoan folyik), kulonben a parolgas/diffuzio
        # elszaradna oket
        if self.stream_mask.any():
            stream_target = 0.35 + 0.6 * self.stream_intensity
            self.water[self.stream_mask] = np.maximum(self.water[self.stream_mask], stream_target[self.stream_mask])

        self.humus -= config.HUMUS_DECAY_RATE * dt
        np.clip(self.humus, 0.0, config.HUMUS_MAX, out=self.humus)
        self._diffuse(self.humus, config.HUMUS_DIFFUSION_RATE)

    def _cell_index(self, x: float, y: float) -> tuple[int, int]:
        col = int(x // self.cell_size)
        row = int(y // self.cell_size)
        col = 0 if col < 0 else (self.cols - 1 if col >= self.cols else col)
        row = 0 if row < 0 else (self.rows - 1 if row >= self.rows else row)
        return row, col

    def get_temperature(self, x: float, y: float) -> float:
        row, col = self._cell_index(x, y)
        return float(self.temperature[row, col])

    def get_water(self, x: float, y: float) -> float:
        row, col = self._cell_index(x, y)
        return float(self.water[row, col])

    def get_humus(self, x: float, y: float) -> float:
        row, col = self._cell_index(x, y)
        return float(self.humus[row, col])

    def add_humus(self, x: float, y: float, amount: float) -> None:
        row, col = self._cell_index(x, y)
        self.humus[row, col] = min(config.HUMUS_MAX, self.humus[row, col] + amount)

    def get_elevation(self, x: float, y: float) -> float:
        row, col = self._cell_index(x, y)
        return float(self.elevation[row, col])

    def get_pressure(self, x: float, y: float) -> float:
        row, col = self._cell_index(x, y)
        return float(self.pressure[row, col])

    def is_deep_water(self, x: float, y: float) -> bool:
        row, col = self._cell_index(x, y)
        return bool(self.is_water[row, col])

    def is_blocked(self, x: float, y: float) -> bool:
        row, col = self._cell_index(x, y)
        return bool(self.blocked[row, col])

    def is_obstacle(self, x: float, y: float) -> bool:
        """Csak a sziklás akadályokat jelzi (állóvizet nem) - ezt használják
        a növények, mert vízbe is gyökeret verhetnek, ha genetikailag elég
        víztűrők (lásd `entities/plant.py`)."""
        row, col = self._cell_index(x, y)
        return bool(self.obstacles[row, col])

    def add_water(self, x: float, y: float, amount: float) -> None:
        row, col = self._cell_index(x, y)
        self.water[row, col] = min(1.0, self.water[row, col] + amount)

    # a terkep-nezet szurokhoz elerheto retegek (lasd `to_rgb_array`)
    MAP_LAYERS = ("normal", "temperature", "water", "humus", "elevation", "pressure")

    def to_rgb_array(self, weather, layer: str = "normal") -> np.ndarray:
        """(cols, rows, 3) alakú uint8 tömb a gyors, felskálázott
        rendereléshez (pygame.surfarray.make_surface elvárja ezt az alakot).

        A `layer` valasztja ki, melyik kornyezeti parametert mutassa a
        terkep: az alapertelmezett "normal" a szokasos, tobb mezot egyszerre
        keverő megjelenites, a tobbi ("temperature", "water", "humus",
        "elevation", "pressure") egy-egy parametert emel ki tiszta
        szin-skalan, hogy konnyen leolvashato legyen az erteke."""
        if layer == "temperature":
            return self._render_layer(self._temp_norm_relative(), (60, 90, 220), (220, 70, 40))
        if layer == "water":
            return self._render_layer(np.clip(self.water, 0.0, 1.0), (110, 95, 60), (40, 120, 220), show_snow=True)
        if layer == "humus":
            return self._render_layer(np.clip(self.humus / config.HUMUS_MAX, 0.0, 1.0), (40, 35, 30), (150, 110, 60))
        if layer == "elevation":
            return self._render_layer(self.elevation, (25, 60, 35), (235, 235, 235))
        if layer == "pressure":
            return self._render_layer(self._pressure_norm_relative(), (150, 60, 190), (230, 200, 70))
        return self._render_normal(weather)

    def get_layer_legend(self, layer: str) -> tuple[tuple[int, int, int], tuple[int, int, int], float, float, str] | None:
        """A `layer` szűrőhöz tartozó szín-skála végpontjait és az azokhoz
        tartozó tényleges értékeket adja vissza (szín_lo, szín_hi, ertek_lo,
        ertek_hi, formatum), hogy a térkép mellé skála-magyarázat legyen
        rajzolható. A "normal" nézethez nincs egyetlen skála (több mezőt
        kever egyszerre), ezért ahhoz None-t ad vissza."""
        if layer == "temperature":
            lo, hi = float(self.temperature.min()), float(self.temperature.max())
            return (60, 90, 220), (220, 70, 40), lo, hi, "{:.0f} C"
        if layer == "water":
            return (110, 95, 60), (40, 120, 220), 0.0, 1.0, "{:.0%}"
        if layer == "humus":
            return (40, 35, 30), (150, 110, 60), 0.0, config.HUMUS_MAX, "{:.1f}"
        if layer == "elevation":
            return (25, 60, 35), (235, 235, 235), self.elevation_min_meters, self.elevation_max_meters, "{:.0f} m"
        if layer == "pressure":
            lo, hi = float(self.pressure.min()), float(self.pressure.max())
            return (150, 60, 190), (230, 200, 70), lo, hi, "{:.0f} hPa"
        return None

    def _temp_norm(self) -> np.ndarray:
        return np.clip((self.temperature + 10.0) / 55.0, 0.0, 1.0)

    def _temp_norm_relative(self) -> np.ndarray:
        """A hőmérséklet-nézethez: a térkép aktuális min-max hőmérséklet
        tartományára nyújtja szét a szín-skálát (nem egy rögzített abszolút
        tartományra), így a domborzatból adódó, jellemzően csak néhány fokos
        eltérés is jól látható marad, függetlenül az aktuális alaphőmérséklettől."""
        lo, hi = self.temperature.min(), self.temperature.max()
        if hi - lo < 1e-6:
            return np.full_like(self.temperature, 0.5)
        return (self.temperature - lo) / (hi - lo)

    def _pressure_norm_relative(self) -> np.ndarray:
        """A legnyomas-nezethez, ugyanolyan relativ (min-max) nyujtassal,
        mint a homerseklet-nezet, hogy a magassagbol adodo kulonbseg jol
        lathato maradjon."""
        lo, hi = self.pressure.min(), self.pressure.max()
        if hi - lo < 1e-6:
            return np.full_like(self.pressure, 0.5)
        return (self.pressure - lo) / (hi - lo)

    def _render_layer(self, norm: np.ndarray, color_lo: tuple, color_hi: tuple, show_snow: bool = False) -> np.ndarray:
        """Egyetlen kornyezeti mezot jelenit meg egy ket szin kozotti
        skalan (color_lo = alacsony ertek, color_hi = magas ertek), a
        sziklas akadalyokat pedig kulon szinnel jelolve terepi tamponthoz.
        `show_snow=True` eseten (pl. a viz-nezeten) a fagypont alatti
        teruletek is a hoval megegyezo szinnel jelennek meg."""
        lo = np.array(color_lo, dtype=np.float64)
        hi = np.array(color_hi, dtype=np.float64)
        rgb = lo + (hi - lo) * np.clip(norm, 0.0, 1.0)[..., None]
        rgb[self.is_water] = np.array(config.COLOR_WATER_BODY, dtype=np.float64)
        if show_snow:
            snow_mask = (self.temperature <= 0.0) & ~self.is_water
            rgb[snow_mask] = np.array(config.COLOR_SNOW, dtype=np.float64)
        rgb = self._blend_streams(rgb, darkness=1.0)
        rgb[self.obstacles] = np.array(config.COLOR_OBSTACLE, dtype=np.float64)
        np.clip(rgb, 0.0, 255.0, out=rgb)
        rgb = rgb.astype(np.uint8)
        return np.transpose(rgb, (1, 0, 2))

    def _blend_streams(self, rgb: np.ndarray, darkness: float) -> np.ndarray:
        """A patak-cellakat (lasd `_recompute_streams`) a `COLOR_STREAM`
        szinnel keveri be a mar kiszamitott terkep-szinekbe: minel nagyobb
        a `stream_intensity`, annal "vizesebb" (annal tobb viz folyt ossze
        ott), ezert annal erosebb a keveres."""
        if not self.stream_mask.any():
            return rgb
        stream_color = np.array(config.COLOR_STREAM, dtype=np.float64) * darkness
        blend = np.where(self.stream_mask, 0.4 + 0.6 * self.stream_intensity, 0.0)
        return rgb * (1.0 - blend)[..., None] + stream_color[None, None, :] * blend[..., None]

    def _render_normal(self, weather) -> np.ndarray:
        temp_norm = self._temp_norm()
        water_norm = np.clip(self.water, 0.0, 1.0)
        humus_norm = np.clip(self.humus / config.HUMUS_MAX, 0.0, 1.0)

        r = 35.0 + temp_norm * 180.0 + humus_norm * 25.0
        g = 35.0 + water_norm * 150.0 - temp_norm * 20.0 + humus_norm * 20.0
        b = 55.0 + water_norm * 190.0 - temp_norm * 45.0 - humus_norm * 15.0

        sun = weather.sunlight_factor()
        darkness = 0.35 + 0.65 * sun

        rgb = np.stack([r, g, b], axis=-1) * darkness
        np.clip(rgb, 0.0, 255.0, out=rgb)
        rgb[self.is_water] = np.array(config.COLOR_WATER_BODY, dtype=np.float64) * darkness
        # 0 fok es az alatt (fagypont) a felszin hoval van beborítva
        snow_mask = (self.temperature <= 0.0) & ~self.is_water
        rgb[snow_mask] = np.array(config.COLOR_SNOW, dtype=np.float64) * darkness
        rgb = self._blend_streams(rgb, darkness)
        rgb[self.obstacles] = np.array(config.COLOR_OBSTACLE, dtype=np.float64) * darkness
        rgb = rgb.astype(np.uint8)
        return np.transpose(rgb, (1, 0, 2))
