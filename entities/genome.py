"""DNS-szerű genetikai kód: normalizált gén-vektor, crossover és mutáció.

Minden gén egy [0,1] tartományba normalizált érték. A tényleges (fajra
jellemző) tulajdonságot a `decode()` állítja elő egy fajspecifikus
(min, max) skálázási táblázat alapján. Így ugyanaz a crossover/mutáció
logika használható minden fajnál, csak a dekódolási skála más.
"""

from __future__ import annotations

import random


def clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


class Genome:
    __slots__ = ("genes",)

    def __init__(self, genes: dict[str, float]):
        self.genes = genes

    @classmethod
    def random(cls, gene_names: list[str]) -> "Genome":
        return cls({name: random.random() for name in gene_names})

    @classmethod
    def seeded(cls, gene_names: list[str], center: float = 0.5, spread: float = 0.25) -> "Genome":
        """Kezdő populációhoz: egy adott érték körüli szórással generált genom,
        hogy induláskor is legyen genetikai diverzitás."""
        return cls({name: clamp01(center + random.uniform(-spread, spread)) for name in gene_names})

    def copy_mutated(self, rate: float, strength: float) -> "Genome":
        """Aszexuális szaporodás: másolat enyhe mutációval."""
        child = dict(self.genes)
        genome = Genome(child)
        return genome.mutate(rate, strength)

    def crossover(self, other: "Genome") -> "Genome":
        """Ivaros szaporodás: génenként véletlenszerűen az egyik szülőtől
        öröklődik, kis eséllyel a kettő átlaga (blend crossover)."""
        child: dict[str, float] = {}
        for name, value_a in self.genes.items():
            value_b = other.genes.get(name, value_a)
            roll = random.random()
            if roll < 0.45:
                child[name] = value_a
            elif roll < 0.9:
                child[name] = value_b
            else:
                child[name] = (value_a + value_b) / 2.0
        return Genome(child)

    def mutate(self, rate: float, strength: float) -> "Genome":
        for name, value in self.genes.items():
            if random.random() < rate:
                self.genes[name] = clamp01(value + random.uniform(-strength, strength))
        return self

    def decode(self, ranges: dict[str, tuple[float, float]]) -> dict[str, float]:
        phenotype: dict[str, float] = {}
        for name, (lo, hi) in ranges.items():
            gene_value = self.genes.get(name, 0.5)
            phenotype[name] = lo + gene_value * (hi - lo)
        return phenotype

    def distance(self, other: "Genome") -> float:
        keys = self.genes.keys()
        total = 0.0
        for key in keys:
            diff = self.genes[key] - other.genes.get(key, 0.5)
            total += diff * diff
        return total ** 0.5

    def to_code_string(self) -> str:
        """Emberi/UI-barát reprezentáció: minden gén -> egy hexa karakter."""
        return "".join(format(int(round(clamp01(v) * 15)), "x") for v in self.genes.values())
