"""Klaszter-elemzes ablak: szuneteltetett szimulacioban a kivalasztott
faj egyedeit csoportositja a genom (DNS-bol szarmazo tulajdonsagok)
alapjan. Egyelore csak K-Means modszerrel, de a `METHODS` szotar bovitheto
tovabbi klaszterezo algoritmusokkal a jovoben."""

from __future__ import annotations

from typing import Callable

import numpy as np
import pygame

import config
from ui.controls import Button, Slider

CLUSTER_COLORS = [
    (231, 76, 60), (52, 152, 219), (46, 204, 113), (241, 196, 15),
    (155, 89, 182), (26, 188, 156), (230, 126, 34), (149, 165, 166),
    (52, 73, 94), (211, 84, 0),
]

METHODS = {
    "kmeans": "K-Means",
}


def _feature_matrix(entities: list, genes: list[str], ranges: dict) -> np.ndarray:
    """Minden gent a sajat (config-beli) ertektartomanyara [0,1]-re
    normalizal, hogy a tavolsagszamitasban ne uraljak a nagy abszolut
    skalaju genek (pl. `lifespan`) a kicsi skalajuakat (pl. `chlorophyll`)."""
    rows = []
    for entity in entities:
        row = []
        for gene in genes:
            lo, hi = ranges[gene]
            value = entity.traits.get(gene, lo)
            span = hi - lo
            row.append((value - lo) / span if span > 1e-9 else 0.0)
        rows.append(row)
    return np.array(rows, dtype=np.float64)


def kmeans(X: np.ndarray, k: int, max_iter: int = 100, seed: int = 0) -> np.ndarray:
    """Egyszeru Lloyd-algoritmusu K-Means; visszaadja minden sorhoz a
    hozzarendelt klaszter-indexet (0..k-1)."""
    n = X.shape[0]
    k = max(1, min(k, n))
    rng = np.random.default_rng(seed)
    centroid_idx = rng.choice(n, size=k, replace=False)
    centroids = X[centroid_idx].copy()
    labels = np.full(n, -1, dtype=int)
    for _ in range(max_iter):
        dists = ((X[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2)
        new_labels = dists.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for ci in range(k):
            mask = labels == ci
            if mask.any():
                centroids[ci] = X[mask].mean(axis=0)
            else:
                # ures klaszter: a jelenleg legrosszabbul illeszkedo pontot
                # jeloljuk ki uj kozepnek, hogy ne "tunjon el" a klaszter
                far_idx = int(dists.min(axis=1).argmax())
                centroids[ci] = X[far_idx]
    return labels


def pca_2d(X: np.ndarray) -> np.ndarray:
    """A tobbdimenzios (normalizalt gen-) terbol 2D vetuletet keszit (fo
    komponens elemzes), hogy a klasztereket szorasdiagramon lehessen
    abrazolni."""
    n = X.shape[0]
    if n == 0:
        return np.zeros((0, 2))
    centered = X - X.mean(axis=0)
    if n < 2 or X.shape[1] < 2:
        return np.zeros((n, 2))
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    components = vt[:2].T
    return centered @ components


class AnalysisWindow:
    """A klaszter-elemzes overlay allapota, rajzolasa es esemenykezelese.
    A `visible` mezot a hivo (main.py) allitja: csak akkor mutatja, ha a
    szimulacio all (szerkeszto mod vagy szunet), es automatikusan elrejti,
    amint a szimulacio ujra fut."""

    SPECIES_LABELS = [
        ("plant", "Novény"),
        ("herbivore", "Novényevő"),
        ("carnivore", "Ragadozó"),
        ("decomposer", "Lebontó"),
    ]

    def __init__(
        self,
        rect: pygame.Rect,
        get_container: Callable[[str], list],
        get_species_meta: Callable[[str], tuple[list, dict]],
    ):
        # a panel szandekosan csak egy also savot foglal el a terkepbol
        # (nem az egeszet), es nincs mogotte elsotetito reteg sem, hogy a
        # terkep tobbi resze - az egyedeken megjeleno klaszter-jelolesekkel
        # egyutt (lasd `draw_world_markers`) - lathato maradjon
        self.rect = rect
        self.visible = False
        self._get_container = get_container
        self._get_species_meta = get_species_meta
        self.species = "plant"
        self.method = "kmeans"
        self.k = 3
        self.result: dict | None = None
        # a legendaban egy klaszterre kattintva ki-be kapcsolhato a
        # lathatosaga (mind a szorasdiagramon, mind a terkepi jelolesnel) -
        # a legenda-sorok kattinthato terulete draw()-ban frissul
        self.hidden_clusters: set[int] = set()
        self._legend_hit_rects: dict[int, pygame.Rect] = {}

        # DNS-osszehasonlitas: ket, a terkepen kivalasztott egyed genjeinek
        # egymas melletti listazasa (barmelyik fajbol, fuggetlenul a
        # klaszterezeshez eppen kivalasztott `species`-tol)
        self.compare_mode = False
        self.compare_picking: str | None = None
        self.compare_entities: dict[str, object | None] = {"a": None, "b": None}
        self._compare_pick_rects: dict[str, pygame.Rect] = {}

        pad = 14
        btn_h = 26
        row_gap = 34
        controls_w = 320
        controls_x = rect.x + pad
        row_y = rect.y + 34

        self.species_buttons: dict[str, Button] = {}
        seg_w = (controls_w - 6 * 3) // 4
        for i, (species, label) in enumerate(self.SPECIES_LABELS):
            bx = controls_x + i * (seg_w + 6)
            self.species_buttons[species] = Button(
                (bx, row_y, seg_w, btn_h), label, self._make_species_setter(species)
            )
        row_y += row_gap

        self.method_buttons: dict[str, Button] = {}
        mseg_w = controls_w // max(1, len(METHODS))
        for i, (key, label) in enumerate(METHODS.items()):
            bx = controls_x + i * mseg_w
            self.method_buttons[key] = Button(
                (bx, row_y, mseg_w - 6, btn_h), label, self._make_method_setter(key)
            )
        row_y += row_gap

        self.k_slider = Slider(
            (controls_x, row_y + 16, controls_w - 100, 10), 2, 10, self.k,
            "Klaszterek szama", on_change=self._set_k, fmt="{:.0f}",
        )
        self.run_button = Button((controls_x + controls_w - 90, row_y, 90, btn_h), "Futtatas", self.run)
        row_y += row_gap

        self.compare_toggle_button = Button(
            (controls_x, row_y, controls_w, btn_h), "DNS osszehasonlitas", self._toggle_compare_mode
        )

        self.close_button = Button((rect.right - pad - 90, rect.y + 6, 90, btn_h), "Bezaras", self.close)

        # a maradek szelesseg (a vezerlok mellett) a szorasdiagramnak jut -
        # ez kiegesziti (nem helyettesiti) a terkepen levo jelolest
        self.plot_rect = pygame.Rect(
            controls_x + controls_w + pad, rect.y + 34, rect.width - controls_w - pad * 3, rect.height - 34 - pad,
        )

        self._sync_toggles()

    def _make_species_setter(self, species: str):
        def _set() -> None:
            self.species = species
            self.result = None
            self._sync_toggles()
        return _set

    def _make_method_setter(self, method: str):
        def _set() -> None:
            self.method = method
            self.result = None
            self._sync_toggles()
        return _set

    def _set_k(self, value: float) -> None:
        self.k = int(round(value))

    def _sync_toggles(self) -> None:
        for species, btn in self.species_buttons.items():
            btn.toggled = species == self.species
        for key, btn in self.method_buttons.items():
            btn.toggled = key == self.method
        self.compare_toggle_button.toggled = self.compare_mode

    def _toggle_compare_mode(self) -> None:
        self.compare_mode = not self.compare_mode
        self.compare_picking = None
        self._sync_toggles()

    def start_picking(self, slot: str) -> None:
        self.compare_picking = None if self.compare_picking == slot else slot

    def assign_compare_entity(self, entity) -> None:
        """A terkepen kattintva kivalasztott egyedet a folyamatban levo
        DNS-osszehasonlito "A"/"B" helyre allitja (lasd main.py, ahova a
        tenyleges terkepi kattintas-eszleles tartozik, hiszen az ablak
        maga nem ismeri a szimulaciot)."""
        slot = self.compare_picking
        self.compare_picking = None
        if slot is None or entity is None:
            return
        self.compare_entities[slot] = entity

    def open(self) -> None:
        self.visible = True

    def close(self) -> None:
        self.visible = False

    def run(self) -> None:
        self.hidden_clusters.clear()
        entities = list(self._get_container(self.species))
        genes, ranges = self._get_species_meta(self.species)
        if not entities:
            self.result = {
                "entities": [], "points": np.zeros((0, 2)), "labels": np.array([], dtype=int),
                "counts": {}, "n": 0,
            }
            return
        features = _feature_matrix(entities, genes, ranges)
        if self.method == "kmeans":
            labels = kmeans(features, self.k)
        else:
            labels = np.zeros(len(entities), dtype=int)
        points = pca_2d(features)
        counts: dict[int, int] = {}
        for label in labels:
            counts[int(label)] = counts.get(int(label), 0) + 1
        self.result = {"entities": entities, "points": points, "labels": labels, "counts": counts, "n": len(entities)}

    def draw_world_markers(self, surface: pygame.Surface) -> None:
        """A klaszterezes eredmenyet magan a szimulacio-terkepen is jelzi:
        minden elemzett egyed korul a sajat klaszterszinevel megegyezo
        szinu gyurut rajzol (a `Simulation._step` mar lefutott adott
        tickre, tehat az egyedek pozicioja a mostani kirajzolt allapotukkal
        egyezik meg). Csak akkor hivjuk (lasd main.py), ha az ablak nyitva
        van es mar volt futtatott elemzes."""
        if self.result is None or self.result["n"] == 0:
            return
        for entity, label in zip(self.result["entities"], self.result["labels"]):
            if not entity.alive or int(label) in self.hidden_clusters:
                continue
            color = CLUSTER_COLORS[int(label) % len(CLUSTER_COLORS)]
            radius = int(entity.traits.get("size", entity.traits.get("max_height", 6.0))) + 6
            pygame.draw.circle(surface, color, (int(entity.x), int(entity.y)), radius, 2)

    def _toggle_cluster_visibility(self, cluster_id: int) -> None:
        if cluster_id in self.hidden_clusters:
            self.hidden_clusters.discard(cluster_id)
        else:
            self.hidden_clusters.add(cluster_id)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        for btn in self.species_buttons.values():
            if btn.handle_event(event):
                return True
        for btn in self.method_buttons.values():
            if btn.handle_event(event):
                return True
        if self.k_slider.handle_event(event):
            return True
        if self.run_button.handle_event(event):
            return True
        if self.close_button.handle_event(event):
            return True
        if self.compare_toggle_button.handle_event(event):
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for cluster_id, hit_rect in self._legend_hit_rects.items():
                if hit_rect.collidepoint(event.pos):
                    self._toggle_cluster_visibility(cluster_id)
                    return True
            if self.compare_mode:
                for slot, hit_rect in self._compare_pick_rects.items():
                    if hit_rect.collidepoint(event.pos):
                        self.start_picking(slot)
                        return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and self.compare_picking is not None:
            self.compare_picking = None
            return True
        # a panel sajat teruletere (a also savra) iranyulo tovabbi eger-
        # esemenyeket elnyeli, hogy ne lehessen "atkattintani" a mogotte
        # levo panelra - de a terkep tobbi reszen tortent kattintast
        # (pl. DNS-osszehasonlitashoz egy egyed kivalasztasa, vagy
        # egyszeru megfigyeles) atengedi a fo programnak
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN:
            return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, font_small: pygame.font.Font) -> None:
        if not self.visible:
            return

        pygame.draw.rect(surface, config.COLOR_PANEL, self.rect, border_radius=8)
        pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, self.rect, 2, border_radius=8)

        title_surf = font.render("Klaszter-elemzés (csak szüneteltetve)", True, config.COLOR_TEXT)
        surface.blit(title_surf, (self.rect.x + 16, self.rect.y + 10))

        for btn in self.species_buttons.values():
            btn.draw(surface, font_small)
        for btn in self.method_buttons.values():
            btn.draw(surface, font_small)
        self.k_slider.draw(surface, font_small)
        self.run_button.draw(surface, font_small)
        self.close_button.draw(surface, font_small)
        self.compare_toggle_button.draw(surface, font_small)

        pygame.draw.rect(surface, (25, 25, 34), self.plot_rect, border_radius=6)
        pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, self.plot_rect, 1, border_radius=6)

        if self.compare_mode:
            self._draw_compare(surface, font_small)
            return

        if self.result is None:
            self._legend_hit_rects = {}
            hint = font_small.render(
                "Valassz fajt es klaszterszamot, majd nyomd meg a Futtatas gombot.",
                True, config.COLOR_TEXT_DIM,
            )
            surface.blit(hint, (self.plot_rect.x + 10, self.plot_rect.y + 10))
            return

        if self.result["n"] == 0:
            self._legend_hit_rects = {}
            hint = font_small.render("Nincs egyed ebbol a fajbol.", True, config.COLOR_TEXT_DIM)
            surface.blit(hint, (self.plot_rect.x + 10, self.plot_rect.y + 10))
            return

        # a legenda annyi sorra tordelodik, amennyi a plot_rect szelessegebe
        # befer, igy sok klaszternel sem log ki a keperny(o)rol/panelrol -
        # eloszor (kirajzolas nelkul) kiszamoljuk a sorokat, hogy tudjuk,
        # mennyi hely marad a szorasdiagramnak felette
        margin = 20
        row_h = 18
        available_w = self.plot_rect.width - margin * 2
        legend_rows: list[list[int]] = [[]]
        row_w = 0.0
        for cluster_id in sorted(self.result["counts"]):
            label_text = f"#{cluster_id}: {self.result['counts'][cluster_id]} db"
            entry_w = 16 + font_small.size(label_text)[0] + 24
            if row_w + entry_w > available_w and legend_rows[-1]:
                legend_rows.append([])
                row_w = 0.0
            legend_rows[-1].append(cluster_id)
            row_w += entry_w

        legend_h = len(legend_rows) * row_h + 6
        plot_w = available_w
        plot_h = self.plot_rect.height - margin * 2 - legend_h

        points = self.result["points"]
        labels = self.result["labels"]
        min_xy = points.min(axis=0)
        max_xy = points.max(axis=0)
        span = np.maximum(max_xy - min_xy, 1e-6)

        for point, label in zip(points, labels):
            if int(label) in self.hidden_clusters:
                continue
            t = (point - min_xy) / span
            px = self.plot_rect.x + margin + int(t[0] * plot_w)
            py = self.plot_rect.y + margin + int((1.0 - t[1]) * plot_h)
            color = CLUSTER_COLORS[int(label) % len(CLUSTER_COLORS)]
            pygame.draw.circle(surface, color, (px, py), 4)

        # a legendasorra kattintva ki-be kapcsolhato az adott klaszter
        # lathatosaga (lasd `handle_event`/`_toggle_cluster_visibility`) -
        # az elrejtett klaszter szurkitve, athuzva jelenik meg
        legend_top = self.plot_rect.bottom - legend_h
        self._legend_hit_rects = {}
        for row_i, row in enumerate(legend_rows):
            legend_x = self.plot_rect.x + margin
            legend_y = legend_top + row_i * row_h
            for cluster_id in row:
                hidden = cluster_id in self.hidden_clusters
                color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]
                swatch_color = config.COLOR_TEXT_DIM if hidden else color
                pygame.draw.circle(surface, swatch_color, (legend_x + 5, legend_y + 6), 5)
                if hidden:
                    pygame.draw.circle(surface, swatch_color, (legend_x + 5, legend_y + 6), 5, 1)
                text_color = config.COLOR_TEXT_DIM if hidden else config.COLOR_TEXT
                label_text = f"#{cluster_id}: {self.result['counts'][cluster_id]} db"
                text = font_small.render(label_text, True, text_color)
                text_pos = (legend_x + 16, legend_y)
                surface.blit(text, text_pos)
                entry_w = 16 + text.get_width() + 24
                if hidden:
                    strike_y = text_pos[1] + text.get_height() // 2
                    pygame.draw.line(surface, text_color, (text_pos[0], strike_y), (text_pos[0] + text.get_width(), strike_y), 1)
                self._legend_hit_rects[cluster_id] = pygame.Rect(legend_x, legend_y, entry_w - 8, row_h)
                legend_x += entry_w

    def _draw_compare(self, surface: pygame.Surface, font_small: pygame.font.Font) -> None:
        """A "DNS osszehasonlitas" mod tartalmat rajzolja a plot_rect
        teruletere: felul az A/B "valassz a terkepen" gombok, alattuk (ha
        mindket egyed ki van valasztva) a genjeik ket oszlopba rendezett,
        egymas melletti listaja."""
        pad = 10
        btn_w = (self.plot_rect.width - pad * 3) // 2
        btn_h = 24
        self._compare_pick_rects = {
            "a": pygame.Rect(self.plot_rect.x + pad, self.plot_rect.y + pad, btn_w, btn_h),
            "b": pygame.Rect(self.plot_rect.x + pad * 2 + btn_w, self.plot_rect.y + pad, btn_w, btn_h),
        }
        for slot, rect in self._compare_pick_rects.items():
            entity = self.compare_entities[slot]
            picking = self.compare_picking == slot
            color = config.COLOR_ACCENT if picking else (55, 55, 68)
            pygame.draw.rect(surface, color, rect, border_radius=4)
            pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, rect, 1, border_radius=4)
            if picking:
                label_text = f"{slot.upper()}: kattints egy egyedre a terkepen..."
            elif entity is not None:
                label_text = f"{slot.upper()}: {type(entity).__name__} #{entity.id}"
            else:
                label_text = f"{slot.upper()}: kattints a valasztashoz"
            text = font_small.render(label_text, True, config.COLOR_TEXT)
            surface.blit(text, text.get_rect(center=rect.center))

        table_top = self.plot_rect.y + pad * 2 + btn_h
        entity_a = self.compare_entities["a"]
        entity_b = self.compare_entities["b"]
        if entity_a is None or entity_b is None:
            hint = font_small.render(
                "Valassz ki ket egyedet a terkepen az osszehasonlitashoz.",
                True, config.COLOR_TEXT_DIM,
            )
            surface.blit(hint, (self.plot_rect.x + pad, table_top))
            return

        genes = sorted(set(entity_a.traits) | set(entity_b.traits))
        row_h = 14
        available_h = self.plot_rect.bottom - pad - table_top
        max_rows = max(1, available_h // row_h)
        col_w = (self.plot_rect.width - pad * 2) // 2
        for i, gene in enumerate(genes):
            col = i // max_rows
            col_x = self.plot_rect.x + pad + col * col_w
            if col_x + col_w > self.plot_rect.right:
                break
            row_y = table_top + (i % max_rows) * row_h
            a_val = entity_a.traits.get(gene)
            b_val = entity_b.traits.get(gene)
            a_text = f"{a_val:.2f}" if a_val is not None else "-"
            b_text = f"{b_val:.2f}" if b_val is not None else "-"
            line = f"{gene}: {a_text} | {b_text}"
            text = font_small.render(line, True, config.COLOR_TEXT)
            surface.blit(text, (col_x, row_y))

    def draw_compare_markers(self, surface: pygame.Surface, font_small: pygame.font.Font) -> None:
        """A DNS-osszehasonlitasra kivalasztott ket egyedet a terkepen is
        megjeloli (feher gyuru + A/B felirat), hogy lathato legyen, melyik
        egyedekrol van szo."""
        for slot, entity in self.compare_entities.items():
            if entity is None or not entity.alive:
                continue
            pos = (int(entity.x), int(entity.y))
            radius = int(entity.traits.get("size", entity.traits.get("max_height", 6.0))) + 10
            pygame.draw.circle(surface, (255, 255, 255), pos, radius, 2)
            label = font_small.render(slot.upper(), True, (255, 255, 255))
            surface.blit(label, (pos[0] + radius, pos[1] - radius))
