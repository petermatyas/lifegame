"""Rács alapú környezeti mezők: hőmérséklet és víz, NumPy-val."""

from __future__ import annotations

import numpy as np

import config


class Environment:
    def __init__(self, cols: int = config.WORLD_COLS, rows: int = config.WORLD_ROWS, cell_size: int = config.CELL_SIZE):
        self.cols = cols
        self.rows = rows
        self.cell_size = cell_size
        self.temperature = np.full((rows, cols), config.DEFAULT_BASE_TEMP, dtype=np.float64)
        self.water = np.random.uniform(0.25, 0.55, size=(rows, cols))

    def _diffuse(self, field: np.ndarray, rate: float) -> None:
        neighbor_avg = (
            np.roll(field, 1, axis=0) + np.roll(field, -1, axis=0)
            + np.roll(field, 1, axis=1) + np.roll(field, -1, axis=1)
        ) / 4.0
        field += (neighbor_avg - field) * rate

    def update(self, dt: float, weather) -> None:
        sun = weather.sunlight_factor()
        target_temp = weather.base_temperature + (sun - 0.5) * 14.0
        if weather.raining:
            target_temp -= 3.0
        self.temperature += (target_temp - self.temperature) * min(1.0, 0.01 * dt)
        self._diffuse(self.temperature, 0.04)

        if weather.raining:
            self.water += weather.rain_intensity * dt * 0.01

        evaporation = 0.0015 * dt * (1.0 + np.clip((self.temperature - 20.0) / 20.0, 0.0, None))
        self.water -= evaporation
        np.clip(self.water, 0.0, 1.0, out=self.water)
        self._diffuse(self.water, 0.06)

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

    def add_water(self, x: float, y: float, amount: float) -> None:
        row, col = self._cell_index(x, y)
        self.water[row, col] = min(1.0, self.water[row, col] + amount)

    def to_rgb_array(self, weather) -> np.ndarray:
        """(cols, rows, 3) alakú uint8 tömb a gyors, felskálázott
        rendereléshez (pygame.surfarray.make_surface elvárja ezt az alakot)."""
        temp_norm = np.clip((self.temperature + 10.0) / 55.0, 0.0, 1.0)
        water_norm = np.clip(self.water, 0.0, 1.0)

        r = 35.0 + temp_norm * 180.0
        g = 35.0 + water_norm * 150.0 - temp_norm * 20.0
        b = 55.0 + water_norm * 190.0 - temp_norm * 45.0

        sun = weather.sunlight_factor()
        darkness = 0.35 + 0.65 * sun

        rgb = np.stack([r, g, b], axis=-1) * darkness
        np.clip(rgb, 0.0, 255.0, out=rgb)
        rgb = rgb.astype(np.uint8)
        return np.transpose(rgb, (1, 0, 2))
