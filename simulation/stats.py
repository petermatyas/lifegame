"""Populáció- és környezet-statisztikák gyűjtése a HUD-grafikonokhoz."""

from __future__ import annotations


def _alive_count(entities: list) -> int:
    return sum(1 for e in entities if not e.pending_removal)


class StatsTracker:
    def __init__(self, max_points: int = 500):
        self.max_points = max_points
        self.history: dict[str, list[float]] = {
            "plants": [],
            "herbivores": [],
            "carnivores": [],
            "decomposers": [],
            "temperature": [],
            "water": [],
            "humus": [],
        }

    def record(self, sim) -> None:
        # a friss elhunytak meg egy tickig a listaban maradnak (lasd
        # `Simulation._mark_newly_dead`), hogy megfigyelhetok legyenek -
        # a statisztikaba viszont mar ne szamitsanak bele elo egyedkent
        self.history["plants"].append(_alive_count(sim.plants))
        self.history["herbivores"].append(_alive_count(sim.herbivores))
        self.history["carnivores"].append(_alive_count(sim.carnivores))
        self.history["decomposers"].append(_alive_count(sim.decomposers))
        self.history["temperature"].append(float(sim.environment.temperature.mean()))
        self.history["water"].append(float(sim.environment.water.mean()))
        self.history["humus"].append(float(sim.environment.humus.mean()))
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
