"""Globális konstansok és alapértelmezett paraméterek."""

# --- Világ / rács ---
WORLD_COLS = 140
WORLD_ROWS = 140
CELL_SIZE = 7

SIM_WIDTH = WORLD_COLS * CELL_SIZE
SIM_HEIGHT = WORLD_ROWS * CELL_SIZE

PANEL_WIDTH = 340
WINDOW_WIDTH = SIM_WIDTH + PANEL_WIDTH
# a panel a szimulacios teruletnel magasabb, hogy a nepesseg- es
# kornyezet-grafikonnak, a feliratainak, a terkep-nezet szuro gomboknak
# es a (kezi + automata) egyed-lehelyezo, domborzat- es inditas-
# gomboknak is jusson hely, es a kivalasztott egyed DNS-reszletezesenek
# is maradjon lathato hely
PANEL_EXTRA_HEIGHT = 380
WINDOW_HEIGHT = SIM_HEIGHT + PANEL_EXTRA_HEIGHT

FPS = 60

# egy "tick" mekkora elmozdulást jelent pixelben sebesség-egységenként
MOVE_SCALE = 6.0

# --- Idő / időjárás alapértékek ---
DAY_LENGTH_TICKS = 1400.0          # egy teljes nap-éjszaka ciklus hossza tickben
DEFAULT_BASE_TEMP = 20.0           # °C
DEFAULT_RAIN_CHANCE = 0.0015       # esély/tick, hogy elkezdjen esni
DEFAULT_RAIN_INTENSITY = 1.0
DEFAULT_TIME_SCALE = 0.25

# --- Allapot-cimkezes viselkedesi kuszobok (lasd entities/states.py) ---
HUNGRY_ENERGY_RATIO = 0.35    # ez alatt az energia-arany alatt az egyed "Ehes" allapotba kerul
SLEEP_MIN_ENERGY_RATIO = 0.6  # ejszaka csak ennel magasabb energiaval "alszik" (kulonben inkabb taplalekot keres)

# --- Domborzat (elevation) és állóvizek ---
ELEVATION_ROUGHNESS = 0.55         # diamond-square: 0-1, minel nagyobb, annal szaggatottabb/sziklasabb a domborzat
ELEVATION_MIN_METERS = -100.0      # a normalizalt (0-1) elevation legalja ennyi meternek felel meg
ELEVATION_MAX_METERS = 1000.0      # a normalizalt (0-1) elevation teteje ennyi meternek felel meg
DEFAULT_WATER_LEVEL_METERS = 0.0   # ez a magassag (m) alatt allando allovíz (to/tenger)
LAKE_WATER_LEVEL = 1.0             # allovíz-cellak vizszintje (nem apad el)
# fok C, amivel 100 meterenkent hul a homerseklet a 0 magassaghoz (tengerszinthez) kepest
DEFAULT_TEMP_GRADIENT_PER_100M = 2

# --- Patakok (a domborzatbol szamitott lefolyas-halmozodas alapjan) ---
# a szarazfoldi cellak lefolyas-halmozodasanak ennyi percentilise felett
# szamit mar "pataknak" (minel magasabb, annal kevesebb, de vizesebb er)
STREAM_ACCUMULATION_PERCENTILE = 95.0
COLOR_STREAM = (70, 140, 210)

# --- Meredek lejtok: a viz onnan lefele folyik, nem marad ott ---
# a relativ meredekseg (`Environment.slope`, 0-1) ez felett kezd el
# vizet elvezetni a lejto-iranyu szomszedba; ez alatt a sima diffuzio
# eleg (nem "nagyon meredek")
STEEP_RUNOFF_THRESHOLD = 0.4
# a legmeredekebb (slope=1.0) cellakon tickenkent a viz ekkora hanyada
# folyik at a lejto-iranyu szomszedba
STEEP_RUNOFF_RATE = 0.05

# --- Legnyomas (kizarolag a magassagbol szamitva, leegyszerusitett barometrikus kozelites) ---
DEFAULT_SEA_LEVEL_PRESSURE = 1013.0    # hPa, a legalacsonyabb (0 m) terepponton
PRESSURE_LAPSE_PER_METER = 0.12        # hPa csokkenes meterenkenti magassagnovekedesnel

# --- Kezdeti populációk és korlátok (túlnépesedés elleni védelem) ---
INITIAL_PLANTS = 220
INITIAL_HERBIVORES = 45
INITIAL_CARNIVORES = 10
INITIAL_DECOMPOSERS = 25

MAX_PLANTS = 550
MAX_HERBIVORES = 220
MAX_CARNIVORES = 70
MAX_DECOMPOSERS = 140

# --- Humusz (a lebontók által termelt tápanyag a talajban) ---
HUMUS_DECAY_RATE = 0.0006          # ennyi humusz vész el időegységenként utánpótlás híján
HUMUS_DIFFUSION_RATE = 0.015       # ennyire terjed szét a szomszédos cellák közt (tickenként)
HUMUS_GROWTH_BONUS = 0.6           # max. ennyivel (pl. 0.6 = +60%) gyorsíthatja a novenyek novekedeset
HUMUS_MAX = 3.0                    # cellankenti humusz-szint felso korlatja

# --- Elhullott entitasok: mekkora hanyaduk valik "detritus" tapanyakka ---
PLANT_CORPSE_RATIO = 0.15
HERBIVORE_CORPSE_RATIO = 0.30
CARNIVORE_CORPSE_RATIO = 0.35
DECOMPOSER_CORPSE_RATIO = 0.10

# --- Genom / fenotípus tartományok fajonként ---
# minden gén [0,1]-re normalizált, a decode(...) skálázza a megadott (min,max) közé

# minden faj DNS-eben szereplo, onmagara vonatkozo mutacios hajlam: a
# szaporodaskor mar nem egy globalis csuszka, hanem az adott szulo(k)
# sajat genje donti el, mennyire (milyen esellyel/mertekben) mutalodjon
# a gyermek genomja - lasd Simulation.reproduce_plants/reproduce_mobile
MUTATION_GENES = ["mutation_rate", "mutation_strength"]
MUTATION_RANGES = {
    "mutation_rate": (0.0, 0.3),
    "mutation_strength": (0.0, 0.5),
}

PLANT_GENES = [
    "growth_rate", "max_energy", "seed_spread", "lifespan",
    "temp_min", "temp_max", "water_need", "drought_resistance",
    "water_tolerance", "chlorophyll", "max_height",
    "germination_water", "germination_humus", "seed_viability", *MUTATION_GENES,
]
PLANT_RANGES = {
    "growth_rate": (0.015, 0.06),
    "max_energy": (50.0, 130.0),
    "seed_spread": (12.0, 70.0),
    "lifespan": (1200.0, 3200.0),
    "temp_min": (-5.0, 15.0),
    "temp_max": (22.0, 42.0),
    "water_need": (0.10, 0.55),
    "drought_resistance": (0.0, 0.6),
    # mennyire birja a tul sok/allando vizet (elarasztott talaj, tofenek):
    # 0.0 = szarazsagkedvelo, elrohad vizes talajban; 1.0 = vizinovenyi,
    # allovízben (tavakban) is korlatlanul megel
    "water_tolerance": (0.0, 1.0),
    # a level zoldjenek arnyalata/melysege (klorofill-tartalom): 0.0 =
    # vilagos, sargas-zold, 1.0 = melyzold - ez hatarozza meg a rajzolt
    # szint (lasd Plant.draw), es a fotoszintezis hatekonysagat is (lasd
    # Plant.update: a novekedes a rea juto fenytol ES ettol a gentol fugg)
    "chlorophyll": (0.0, 1.0),
    # a noveny vegso, kifejlett magassaga/lombmerete: minel nagyobb, annal
    # tobb fenyet fog el a sajat szuk kornyezeteben a nala kisebb
    # novenyektol (lasd Plant.update: `_shade_factor` es PLANT_SHADE_*)
    "max_height": (3.0, 16.0),
    # a magnak (lasd Plant `is_seed` allapota) legalabb ennyi viz/humusz
    # kell a kicsirazashoz (a homerseklet-igenyt a mar meglevo temp_min/
    # temp_max gen szabja meg) - lasd Plant._update_seed
    "germination_water": (0.05, 0.35),
    "germination_humus": (0.0, 0.4),
    # ennyi ticket varhat egy mag kicsirazasra alkalmas korulmenyekre,
    # mielott (kicsirazas hianyaban) elpusztul - lasd Plant._update_seed
    "seed_viability": (150.0, 600.0),
    **MUTATION_RANGES,
}

# ennyivel a `water_need` felett szamit mar "tul sok" viznek (lasd Plant.update)
PLANT_FLOOD_MARGIN = 0.25

# --- Novenyek egymast arnyekolasa (a `max_height` gen alapjan) ---
# egy noveny arnyeka a sajat (aktualis, energia-aranyos) magassaganak
# ennyiszerese tavolsagig er el
PLANT_SHADE_RADIUS_FACTOR = 2.0
# egy telejsen kifejlett, sokkal nagyobb szomszed legfeljebb ekkora
# hanyaddal csokkentheti a kisebb noveny fotoszintezishez juto fenyet
PLANT_SHADE_MAX_FACTOR = 0.7

# --- Novenyi mag es tetem eletciklus ---
# a mag a max_energy ekkora hanyadaval indul (kis tartalek a
# kicsirazasig) - lasd Plant.__init__
PLANT_SEED_ENERGY_RATIO = 0.05
# elpusztulaskor (kicsirazatlan mag vagy kifejlett noveny) a tetem
# kezdeti "tomege" a max_energy ekkora hanyada - ez fogy el fokozatosan
# (lasd Plant._update_corpse), nem valik kulon Detritus-sza
PLANT_CORPSE_DECAY_BASE_RATE = 0.01     # a kezdeti tetem-tomeg ekkora hanyada fogy el tickenkent, referencia-homersekleten
PLANT_CORPSE_DECAY_TEMP_REF = 20.0      # °C, ehhez kepest gyorsul/lassul a bomlas
PLANT_CORPSE_DECAY_TEMP_COEFF = 0.05    # ennyivel szorzodik/no a bomlasi utem fokonkent a referenciahoz kepest
PLANT_CORPSE_DECAY_MIN_MULT = 0.2       # nagyon hideg helyen sem all le teljesen a bomlas
PLANT_CORPSE_DECAY_MAX_MULT = 3.0       # nagyon meleg helyen legfeljebb ennyiszeresere gyorsul
# a tetembol tickenkent elfogyo tomeg ekkora hanyada valik kozvetlenul
# humusszá a tetem helyen (lebonto szervezetek nelkul is) - lasd
# Plant._update_corpse
PLANT_CORPSE_HUMUS_YIELD = 0.6

HERBIVORE_GENES = [
    "speed", "size", "vision_range", "metabolism_rate", "max_energy",
    "fertility", "lifespan", "temp_min", "temp_max", "water_need",
    "bite_size", "flee_bonus", "camouflage", *MUTATION_GENES,
]
HERBIVORE_RANGES = {
    "speed": (0.5, 1.8),
    "size": (4.0, 9.0),
    "vision_range": (60.0, 170.0),
    "metabolism_rate": (0.015, 0.05),
    "max_energy": (90.0, 190.0),
    "fertility": (0.3, 1.0),
    "lifespan": (1000.0, 2600.0),
    "temp_min": (-10.0, 8.0),
    "temp_max": (24.0, 44.0),
    "water_need": (0.08, 0.4),
    "bite_size": (3.0, 9.0),
    "flee_bonus": (0.0, 1.1),
    "camouflage": (0.0, 1.0),
    **MUTATION_RANGES,
}

CARNIVORE_GENES = [
    "speed", "size", "vision_range", "metabolism_rate", "max_energy",
    "fertility", "lifespan", "temp_min", "temp_max", "water_need",
    "attack_power", "camouflage", *MUTATION_GENES,
]
CARNIVORE_RANGES = {
    "speed": (0.6, 2.0),
    "size": (5.0, 11.0),
    "vision_range": (80.0, 220.0),
    "metabolism_rate": (0.02, 0.055),
    "max_energy": (110.0, 240.0),
    "fertility": (0.2, 0.85),
    "lifespan": (1200.0, 3000.0),
    "temp_min": (-8.0, 8.0),
    "temp_max": (24.0, 44.0),
    "water_need": (0.08, 0.4),
    "attack_power": (0.1, 1.0),
    "camouflage": (0.0, 1.0),
    **MUTATION_RANGES,
}

DECOMPOSER_GENES = [
    "speed", "size", "vision_range", "metabolism_rate", "max_energy",
    "fertility", "lifespan", "temp_min", "temp_max", "water_need",
    "decomposition_rate", "humus_yield", *MUTATION_GENES,
]
DECOMPOSER_RANGES = {
    "speed": (0.05, 0.3),           # jelentosen lassabb, mint a novenyevo/ragadozo
    "size": (3.0, 7.0),
    "vision_range": (25.0, 80.0),
    "metabolism_rate": (0.008, 0.025),
    "max_energy": (40.0, 100.0),
    "fertility": (0.3, 1.0),
    "lifespan": (700.0, 1900.0),
    "temp_min": (-4.0, 10.0),
    "temp_max": (20.0, 40.0),
    "water_need": (0.15, 0.5),
    "decomposition_rate": (1.5, 8.0),   # detritus-egyseg/tick, amit le tud bontani
    "humus_yield": (0.35, 0.85),        # a lebontott anyag hany hanyada lesz humusz
    **MUTATION_RANGES,
}

# --- Terepakadályok (sziklák / hegyek) ---
OBSTACLE_CLUSTER_COUNT = 14        # hány sziklatömb generálódjon
OBSTACLE_CLUSTER_SIZE = (3, 10)    # egy tömb hossza cellákban (min, max)

# --- Színek (sötét téma) ---
COLOR_BG = (18, 18, 24)
COLOR_PANEL = (26, 26, 34)
COLOR_PANEL_BORDER = (55, 55, 68)
COLOR_TEXT = (225, 225, 232)
COLOR_TEXT_DIM = (150, 150, 162)
COLOR_ACCENT = (90, 160, 220)

COLOR_OBSTACLE = (92, 88, 80)
COLOR_WATER_BODY = (38, 92, 162)
COLOR_SNOW = (235, 240, 250)

COLOR_PLANT = (70, 200, 90)
COLOR_HERBIVORE = (80, 150, 235)
COLOR_CARNIVORE = (235, 90, 80)
COLOR_DECOMPOSER = (150, 110, 60)
