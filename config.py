"""Globális konstansok és alapértelmezett paraméterek."""

# --- Világ / rács ---
WORLD_COLS = 70
WORLD_ROWS = 60
CELL_SIZE = 14

SIM_WIDTH = WORLD_COLS * CELL_SIZE
SIM_HEIGHT = WORLD_ROWS * CELL_SIZE

PANEL_WIDTH = 340
WINDOW_WIDTH = SIM_WIDTH + PANEL_WIDTH
# a panel a szimulacios teruletnel magasabb, hogy a nepesseg- es
# kornyezet-grafikonnak es a felirataiknak is jusson hely
PANEL_EXTRA_HEIGHT = 170
WINDOW_HEIGHT = SIM_HEIGHT + PANEL_EXTRA_HEIGHT

FPS = 60

# egy "tick" mekkora elmozdulást jelent pixelben sebesség-egységenként
MOVE_SCALE = 6.0

# --- Idő / időjárás alapértékek ---
DAY_LENGTH_TICKS = 1400.0          # egy teljes nap-éjszaka ciklus hossza tickben
DEFAULT_BASE_TEMP = 20.0           # °C
DEFAULT_RAIN_CHANCE = 0.0015       # esély/tick, hogy elkezdjen esni
DEFAULT_RAIN_INTENSITY = 1.0
DEFAULT_MUTATION_RATE = 0.06
DEFAULT_MUTATION_STRENGTH = 0.12
DEFAULT_TIME_SCALE = 0.25

# --- Kezdeti populációk és korlátok (túlnépesedés elleni védelem) ---
INITIAL_PLANTS = 220
INITIAL_HERBIVORES = 45
INITIAL_CARNIVORES = 10

MAX_PLANTS = 550
MAX_HERBIVORES = 220
MAX_CARNIVORES = 70

# --- Genom / fenotípus tartományok fajonként ---
# minden gén [0,1]-re normalizált, a decode(...) skálázza a megadott (min,max) közé

PLANT_GENES = [
    "growth_rate", "max_energy", "seed_spread", "lifespan",
    "temp_min", "temp_max", "water_need", "drought_resistance",
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
}

HERBIVORE_GENES = [
    "speed", "size", "vision_range", "metabolism_rate", "max_energy",
    "fertility", "lifespan", "temp_min", "temp_max", "water_need",
    "bite_size", "flee_bonus", "camouflage",
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
}

CARNIVORE_GENES = [
    "speed", "size", "vision_range", "metabolism_rate", "max_energy",
    "fertility", "lifespan", "temp_min", "temp_max", "water_need",
    "attack_power", "camouflage",
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

COLOR_PLANT = (70, 200, 90)
COLOR_HERBIVORE = (80, 150, 235)
COLOR_CARNIVORE = (235, 90, 80)
