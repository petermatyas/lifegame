"""Detritus: elhullott entitásokból keletkező szerves törmelék, amit a
lebontó szervezetek (Decomposer) humusszá alakítanak."""

from __future__ import annotations


class Detritus:
    __slots__ = ("x", "y", "energy")

    def __init__(self, x: float, y: float, energy: float):
        self.x = x
        self.y = y
        self.energy = energy

    @property
    def alive(self) -> bool:
        return self.energy > 0.05
