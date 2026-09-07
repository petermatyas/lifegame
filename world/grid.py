"""Egyszerű térbeli hash-rács a "legközelebbi szomszéd" keresés
gyorsítására, hogy ne kelljen minden entitást minden entitással
összehasonlítani (O(n^2) elkerülése nagy populációnál)."""

from __future__ import annotations


class SpatialGrid:
    def __init__(self, width: float, height: float, cell_size: float = 40.0):
        self.cell_size = cell_size
        self.cols = int(width // cell_size) + 2
        self.rows = int(height // cell_size) + 2
        self.buckets: dict[tuple[int, int], list] = {}

    def clear(self) -> None:
        self.buckets.clear()

    def _key(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def build(self, entities) -> None:
        self.clear()
        for entity in entities:
            self.buckets.setdefault(self._key(entity.x, entity.y), []).append(entity)

    def query_radius(self, x: float, y: float, radius: float) -> list:
        results = []
        cell_span = int(radius // self.cell_size) + 1
        cx, cy = self._key(x, y)
        for dx in range(-cell_span, cell_span + 1):
            for dy in range(-cell_span, cell_span + 1):
                bucket = self.buckets.get((cx + dx, cy + dy))
                if bucket:
                    results.extend(bucket)
        return results
