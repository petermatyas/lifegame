"""Populáció-statisztikák gyűjtése a HUD-grafikonhoz."""

from __future__ import annotations


class StatsTracker:
    def __init__(self, max_points: int = 500):
        self.max_points = max_points
        self.history: dict[str, list[int]] = {
            "plants": [],
            "herbivores": [],
            "carnivores": [],
        }

    def record(self, sim) -> None:
        self.history["plants"].append(len(sim.plants))
        self.history["herbivores"].append(len(sim.herbivores))
        self.history["carnivores"].append(len(sim.carnivores))
        for key, series in self.history.items():
            if len(series) > self.max_points:
                del series[: len(series) - self.max_points]

    def max_value(self) -> int:
        best = 1
        for series in self.history.values():
            if series:
                best = max(best, max(series))
        return best
