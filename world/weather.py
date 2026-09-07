"""Idő, nappal/éjszaka ciklus és eső/szárazság kezelése.

Minden paraméter (alap hőmérséklet, eső esélye/intenzitása, időskálázás,
pause) kívülről (UI-ból) is állítható -- ez a "kontrolálható környezet és
idő" követelmény megvalósítása.
"""

from __future__ import annotations

import math
import random

import config


class Weather:
    def __init__(self):
        self.time_of_day = 0.25  # 0..1, 0.5 = dél
        self.day_length = config.DAY_LENGTH_TICKS
        self.day_count = 0

        self.base_temperature = config.DEFAULT_BASE_TEMP
        self.rain_chance_per_tick = config.DEFAULT_RAIN_CHANCE
        self.rain_intensity = config.DEFAULT_RAIN_INTENSITY

        self.raining = False
        self.rain_timer = 0.0
        # None = automata, True/False = manuális felülbírálás
        self.manual_rain_override: bool | None = None

        self.time_scale = config.DEFAULT_TIME_SCALE
        self.paused = False

    def update(self, dt: float) -> None:
        prev_time = self.time_of_day
        self.time_of_day += dt / self.day_length
        if self.time_of_day >= 1.0:
            self.time_of_day -= 1.0
            self.day_count += 1

        if self.manual_rain_override is True:
            self.raining = True
        elif self.manual_rain_override is False:
            self.raining = False
        else:
            if not self.raining:
                if random.random() < self.rain_chance_per_tick * dt:
                    self.raining = True
                    self.rain_timer = random.uniform(80.0, 260.0)
            else:
                self.rain_timer -= dt
                if self.rain_timer <= 0:
                    self.raining = False

    def sunlight_factor(self) -> float:
        """0..1 érték: 0 = teljes sötétség (éjszaka), 1 = déli napsütés."""
        return max(0.0, math.sin(2 * math.pi * (self.time_of_day - 0.25)))

    def is_day(self) -> bool:
        return self.sunlight_factor() > 0.05
