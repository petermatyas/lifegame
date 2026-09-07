"""Populáció- és környezet-statisztikák gyűjtése a HUD-grafikonokhoz."""

from __future__ import annotations


class StatsTracker:
    def __init__(self, max_points: int = 500):
        self.max_points = max_points
        self.history: dict[str, list[float]] = {
            "plants": [],
            "herbivores": [],
            "carnivores": [],
            "temperature": [],
            "water": [],
        }

    def record(self, sim) -> None:
        self.history["plants"].append(len(sim.plants))
        self.history["herbivores"].append(len(sim.herbivores))
        self.history["carnivores"].append(len(sim.carnivores))
        self.history["temperature"].append(float(sim.environment.temperature.mean()))
        self.history["water"].append(float(sim.environment.water.mean()))
        for key, series in self.history.items():
            if len(series) > self.max_points:
                del series[: len(series) - self.max_points]

    def max_value(self, keys: list[str]) -> float:
        best = 1.0
        for key in keys:
            series = self.history[key]
            if series:
                best = max(best, max(series))
        return best

    def min_value(self, keys: list[str]) -> float:
        best = 0.0
        seen = False
        for key in keys:
            series = self.history[key]
            if series:
                lowest = min(series)
                best = lowest if not seen else min(best, lowest)
                seen = True
        return best
