"""Elet Szimulacio - belepesi pont.

A program mar legeneralt domborzattal, de nepesseg nelkul indul
(szerkeszto mod): a domborzat ujra is generalhato, majd novenyeket/
allatokat lehet lehelyezni (kezzel kattintassal vagy automatikus
generalassal), es csak a "Szimulacio inditasa" gomb inditja el az idot.

Iranyitas:
  SPACE - szunet/folytatas
  S     - egy lepes (szunet alatt)
  R     - ujrainditas (uj domborzattal, ures szerkeszto modba ter vissza)
  Egeret kattintva a vilagra: entitas kivalasztasa, vagy uj egyed
  lehelyezese, ha eppen aktiv egy "+ ... lehelyezese" gomb.
  Kivalasztott egyednel a DNS sorra kattintva a genom reszletes
  (gen -> nyers ertek -> tulajdonsag) bontasa jelenik meg.
"""

from __future__ import annotations

import sys

import pygame

import config
from simulation.engine import Simulation
from ui.controls import Slider, Button, SectionHeader, Label
from ui.hud import draw_hud, draw_population_graph, draw_environment_graph, draw_map_legend
from ui.inspector import find_clicked_entity, draw_inspector, get_dns_line_rect
from ui.analysis import AnalysisWindow


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Elet Szimulacio")

    # ha a kepernyo kisebb, mint az alapertelmezett ablakmeret, ne logjon ki
    # az ablak teteje/alja a lathato teruletrol (pl. kisebb felbontasu vagy
    # taszkbar/cimsor miatt szukebb kijelzoknel)
    display_info = pygame.display.Info()
    max_height = max(480, display_info.current_h - 90)
    if config.WINDOW_HEIGHT > max_height:
        config.WINDOW_HEIGHT = max_height

    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)
    font_small = pygame.font.SysFont("consolas", 12)

    sim = Simulation()

    panel_x = config.SIM_WIDTH
    panel_rect = pygame.Rect(panel_x, 0, config.PANEL_WIDTH, config.WINDOW_HEIGHT)

    pending_spawn: dict[str, str | None] = {"species": None}
    inspector_state = {"dna_expanded": False}

    def set_pending(species: str) -> None:
        pending_spawn["species"] = species

    def select_entity(entity) -> None:
        if entity is not sim.selected_entity:
            inspector_state["dna_expanded"] = False
        sim.selected_entity = entity

    def toggle_pause() -> None:
        sim.weather.paused = not sim.weather.paused
        pause_button.text = "Folytatas" if sim.weather.paused else "Szunet"
        pause_button.toggled = sim.weather.paused

    def do_step() -> None:
        sim.weather.paused = True
        pause_button.text = "Folytatas"
        pause_button.toggled = True
        sim.step_once()

    def do_reset() -> None:
        sim.reset()
        pause_button.text = "Szunet"
        pause_button.toggled = False
        update_start_button_text()

    def do_start() -> None:
        sim.start()
        update_start_button_text()

    def update_start_button_text() -> None:
        start_button.text = "Szimulacio fut" if sim.started else "Szimulacio inditasa"
        start_button.toggled = sim.started

    def do_regenerate_terrain() -> None:
        sim.regenerate_terrain()

    def sim_is_running() -> bool:
        return sim.started and not sim.weather.paused

    SPECIES_CONTAINERS = {
        "plant": lambda: sim.plants,
        "herbivore": lambda: sim.herbivores,
        "carnivore": lambda: sim.carnivores,
        "decomposer": lambda: sim.decomposers,
    }
    SPECIES_GENE_META = {
        "plant": (config.PLANT_GENES, config.PLANT_RANGES),
        "herbivore": (config.HERBIVORE_GENES, config.HERBIVORE_RANGES),
        "carnivore": (config.CARNIVORE_GENES, config.CARNIVORE_RANGES),
        "decomposer": (config.DECOMPOSER_GENES, config.DECOMPOSER_RANGES),
    }

    def get_species_container(species: str) -> list:
        return SPECIES_CONTAINERS[species]()

    def get_species_meta(species: str) -> tuple[list, dict]:
        return SPECIES_GENE_META[species]

    # also sav a terkep aljan, nem az egesz szimulacios terulet - igy a
    # terkep tobbi resze (a klaszterek szerint szinezett egyedjelolesekkel
    # egyutt, lasd `AnalysisWindow.draw_world_markers`) lathato marad,
    # amig az elemzo ablak nyitva van
    ANALYSIS_BAR_H = 190
    analysis_rect = pygame.Rect(0, config.SIM_HEIGHT - ANALYSIS_BAR_H, config.SIM_WIDTH, ANALYSIS_BAR_H)
    analysis_window = AnalysisWindow(analysis_rect, get_species_container, get_species_meta)

    def open_analysis() -> None:
        # csak akkor nyithato meg, ha a szimulacio all (szerkeszto mod
        # vagy szunet) - lasd `sim_is_running` / a fo ciklusban levo
        # automatikus bezaras, amint a szimulacio ujra futni kezd
        if not sim_is_running():
            analysis_window.open()

    # a "Kezdo letszam" csuszkak allitjak, az "Auto" gombok ennyit
    # helyeznek el egyszerre (a felhasznalo szabja meg, mennyi allat/
    # noveny induljon automatikusan generalva)
    auto_counts = {
        "plant": config.INITIAL_PLANTS,
        "herbivore": config.INITIAL_HERBIVORES,
        "carnivore": config.INITIAL_CARNIVORES,
        "decomposer": config.INITIAL_DECOMPOSERS,
    }

    def make_auto_spawn(species: str):
        def _spawn() -> None:
            sim.populate_species_random(species, int(auto_counts[species]))
        return _spawn

    auto_buttons: dict[str, Button] = {}

    def make_count_handler(species: str):
        def _update(v: float) -> None:
            count = int(round(v))
            auto_counts[species] = count
            btn = auto_buttons.get(species)
            if btn is not None:
                btn.text = f"Auto +{count}"
        return _update

    def cycle_rain() -> None:
        current = sim.weather.manual_rain_override
        if current is None:
            sim.weather.manual_rain_override = True
        elif current is True:
            sim.weather.manual_rain_override = False
        else:
            sim.weather.manual_rain_override = None
        update_rain_button_text()

    def update_rain_button_text() -> None:
        current = sim.weather.manual_rain_override
        if current is None:
            rain_button.text = "Eso: Automata"
        elif current is True:
            rain_button.text = "Eso: Kenyszeritve BE"
        else:
            rain_button.text = "Eso: Kenyszeritve KI"

    x = panel_x + 20
    w = config.PANEL_WIDTH - 40
    y = 28

    BTN_H = 26
    GAP_BTN_BTN = 27     # gomb utan gomb (nincs felirat, ami helyet kerne)
    GAP_BTN_SLIDER = 44  # gomb utan csuszka (a csuszka felirata fole kell hely)
    GAP_SLIDER_SLIDER = 28
    GAP_SLIDER_BTN = 15
    GAP_HEADER_COLLAPSED = 8  # osszecsukott szakasz-fejlecek kozotti (kisebb) tavolsag
    half = w // 2 - 5

    class GraphPanel:
        """A nepesseg-/kornyezet-grafikonokat (lasd ui/hud.py) csomagolja
        egy Slider/Button-szeru "widget" interfeszbe (.rect + .draw), hogy
        ugyanugy resze lehessenek egy osszecsukhato szakasznak."""

        def __init__(self, rect: pygame.Rect, draw_fn) -> None:
            self.rect = rect
            self._draw_fn = draw_fn

        def handle_event(self, event: pygame.event.Event) -> bool:
            return False

        def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
            self._draw_fn(surface, self.rect, font, sim.stats)

    class SectionBuilder:
        """Egy osszecsukhato oldalsav-szakaszt epit fel: a `slider`/`button`/
        `label` hivasok a mostani `y` kurzorra helyezik az uj vezerlot, es
        (widget, nominalis-y) parkent eltarolja oket, hogy a `layout_sections`
        kesobb - a szakasz osszecsukott allapotatol fuggoen - at tudja
        pozicionalni oket."""

        def __init__(self, title: str, top_y: int) -> None:
            self.header = SectionHeader((x, top_y, w, BTN_H), title)
            self.top = top_y
            self.y = top_y + GAP_BTN_SLIDER
            self.items: list[tuple[object, int]] = []

        def slider(self, *args, **kwargs) -> Slider:
            widget = Slider((x, self.y, w, 10), *args, **kwargs)
            self.items.append((widget, self.y))
            return widget

        def button(self, bx: int, bw: int, text: str, on_click) -> Button:
            widget = Button((bx, self.y, bw, BTN_H), text, on_click)
            self.items.append((widget, self.y))
            return widget

        def label(self, text: str) -> Label:
            widget = Label((x, self.y), text)
            self.items.append((widget, self.y))
            return widget

        def custom(self, widget) -> object:
            self.items.append((widget, self.y))
            return widget

        def gap(self, dy: int) -> None:
            self.y += dy

        def finish(self) -> dict:
            return {"header": self.header, "items": self.items, "top": self.top, "bottom": self.y}

    sections: list[dict] = []

    pause_button = Button((x, y, w // 2 - 5, BTN_H), "Szunet", toggle_pause)
    step_button = Button((x + w // 2 + 5, y, w // 2 - 5, BTN_H), "Lepes", do_step)
    y += GAP_BTN_BTN
    reset_button = Button((x, y, w, BTN_H), "Ujrainditas (R)", do_reset)
    y += GAP_BTN_BTN
    start_button = Button((x, y, w, BTN_H), "Szimulacio inditasa", do_start)
    y += GAP_BTN_BTN
    analysis_button = Button((x, y, w, BTN_H), "Elemzes (klaszterezes)", open_analysis)
    y += GAP_BTN_SLIDER

    speed_slider = Slider(
        (x, y, w, 10), 0.1, 8.0, sim.weather.time_scale, "Sebesseg",
        on_change=lambda v: setattr(sim.weather, "time_scale", v), fmt="{:.1f}x",
    )
    y += GAP_SLIDER_SLIDER

    always_widgets = [pause_button, step_button, reset_button, start_button, analysis_button, speed_slider]

    # --- "Idojaras" szakasz ---
    sb = SectionBuilder("Idojaras", y)
    temp_slider = sb.slider(
        -10.0, 40.0, sim.weather.base_temperature, "Alaphomerseklet",
        on_change=lambda v: setattr(sim.weather, "base_temperature", v), fmt="{:.0f} C",
    )
    sb.gap(GAP_SLIDER_SLIDER)
    rain_chance_slider = sb.slider(
        0.0, 0.01, sim.weather.rain_chance_per_tick, "Eso eselye",
        on_change=lambda v: setattr(sim.weather, "rain_chance_per_tick", v), fmt="{:.4f}",
    )
    sb.gap(GAP_SLIDER_SLIDER)
    rain_intensity_slider = sb.slider(
        0.0, 3.0, sim.weather.rain_intensity, "Eso intenzitasa",
        on_change=lambda v: setattr(sim.weather, "rain_intensity", v), fmt="{:.2f}",
    )
    sb.gap(GAP_SLIDER_BTN)
    rain_button = sb.button(x, w, "Eso: Automata", cycle_rain)
    sb.gap(GAP_BTN_BTN)
    y = sb.y
    sections.append(sb.finish())

    # --- "Terkep nezet (szuro)" szakasz ---
    # Melyik kornyezeti parametert szinezze ki a terkep (lasd
    # Environment.to_rgb_array/MAP_LAYERS). Egyszerre csak egy lehet aktiv,
    # ezert a kivalasztott gomb kivetelevel mindet lekapcsoljuk. Kulon
    # szakasz, hogy egy gombbal (a fejlecere kattintva) el lehessen
    # rejteni/ujra megjeleniteni, fuggetlenul a domborzat-beallitasoktol.
    map_view_state = {"layer": "normal"}
    map_layer_buttons: dict[str, Button] = {}

    def select_map_layer(layer: str) -> None:
        map_view_state["layer"] = layer
        for name, btn in map_layer_buttons.items():
            btn.toggled = name == layer

    sb = SectionBuilder("Terkep nezet (szuro)", y)
    map_layer_rows = [
        [("normal", "Normal"), ("temperature", "Homerseklet")],
        [("water", "Viz"), ("humus", "Humusz")],
        [("elevation", "Magassag"), ("pressure", "Legnyomas")],
    ]
    for row_i, row in enumerate(map_layer_rows):
        for col_i, (layer, label_text) in enumerate(row):
            btn_w = w if len(row) == 1 else half
            btn_x = x if col_i == 0 else x + half + 10
            btn = sb.button(btn_x, btn_w, label_text, lambda ly=layer: select_map_layer(ly))
            btn.toggled = layer == map_view_state["layer"]
            map_layer_buttons[layer] = btn
        is_last_row = row_i == len(map_layer_rows) - 1
        sb.gap(GAP_BTN_SLIDER if is_last_row else GAP_BTN_BTN)
    y = sb.y
    sections.append(sb.finish())

    # --- "Domborzat" szakasz ---
    sb = SectionBuilder("Domborzat", y)
    terrain_button = sb.button(x, w, "Domborzat ujragenerálasa", do_regenerate_terrain)
    sb.gap(GAP_BTN_SLIDER)

    temp_gradient_slider = sb.slider(
        0.0, 2.0, sim.environment.temp_gradient_per_100m, "Homerseklet gradiens (C/100m)",
        on_change=lambda v: sim.environment.set_temp_gradient_per_100m(v), fmt="{:.2f}",
    )
    sb.gap(GAP_SLIDER_SLIDER)

    def set_elevation_min(v: float) -> None:
        sim.environment.set_elevation_range_meters(v, sim.environment.elevation_max_meters)

    elevation_min_slider = sb.slider(
        -500.0, 500.0, sim.environment.elevation_min_meters, "Min magassag",
        on_change=set_elevation_min, fmt="{:.0f} m",
    )
    sb.gap(GAP_SLIDER_SLIDER)

    def set_elevation_max(v: float) -> None:
        sim.environment.set_elevation_range_meters(sim.environment.elevation_min_meters, v)

    elevation_max_slider = sb.slider(
        100.0, 5000.0, sim.environment.elevation_max_meters, "Max magassag",
        on_change=set_elevation_max, fmt="{:.0f} m",
    )
    sb.gap(GAP_SLIDER_SLIDER)

    water_level_slider = sb.slider(
        -500.0, 5000.0, sim.environment.water_level_meters, "Viz szintje",
        on_change=lambda v: sim.environment.set_water_level_meters(v), fmt="{:.0f} m",
    )
    sb.gap(GAP_SLIDER_SLIDER)
    y = sb.y
    sections.append(sb.finish())

    # A mutacios rata/erosseg es a novenyek viztures kepessege mostmar a
    # DNS resze (lasd config.MUTATION_GENES / PLANT_GENES), egyedenkent
    # evolvalodik - nincs tobbe kulon globalis "Genetika" csuszka-szakasz.

    # --- "Kezdo populaciok" szakasz ---
    # Fajonkent: (species, csuszka-felirat, kezi gomb felirat, max letszam).
    # A csuszkak es a gomb-sorok kulon csoportban vannak (nem fajonkent
    # egymas alatt), mert igy sokkal kevesebb, draga "gomb utani csuszka"
    # tipusu (nagy) atmenetre van szukseg -> kompaktabb panel.
    SPECIES_ROWS = [
        ("plant", "Kezdo novenyek", "+ Noveny", config.MAX_PLANTS),
        ("herbivore", "Kezdo novenyevok", "+ Novenyevo", config.MAX_HERBIVORES),
        ("carnivore", "Kezdo ragadozok", "+ Ragadozo", config.MAX_CARNIVORES),
        ("decomposer", "Kezdo lebontok", "+ Lebonto", config.MAX_DECOMPOSERS),
    ]

    sb = SectionBuilder("Kezdo populaciok", y)
    sb.label("Uj egyed: kezzel vagy automatikusan")
    sb.gap(30)
    count_sliders = []

    for i, (species, label_text, _manual_label, max_count) in enumerate(SPECIES_ROWS):
        count_sliders.append(sb.slider(
            0, max_count, auto_counts[species], label_text,
            on_change=make_count_handler(species), fmt="{:.0f} db",
        ))
        sb.gap(GAP_SLIDER_BTN if i == len(SPECIES_ROWS) - 1 else GAP_SLIDER_SLIDER)

    spawn_buttons_by_species = {}
    for i, (species, _label, manual_label, _max_count) in enumerate(SPECIES_ROWS):
        spawn_btn = sb.button(x, half, manual_label, lambda sp=species: set_pending(sp))
        auto_btn = sb.button(
            x + half + 10, half, f"Auto +{auto_counts[species]}",
            make_auto_spawn(species),
        )
        auto_buttons[species] = auto_btn
        spawn_buttons_by_species[species] = (spawn_btn, auto_btn)
        sb.gap(GAP_BTN_SLIDER if i == len(SPECIES_ROWS) - 1 else GAP_BTN_BTN)

    spawn_plant_btn, auto_plant_btn = spawn_buttons_by_species["plant"]
    spawn_herb_btn, auto_herb_btn = spawn_buttons_by_species["herbivore"]
    spawn_carn_btn, auto_carn_btn = spawn_buttons_by_species["carnivore"]
    spawn_decomp_btn, auto_decomp_btn = spawn_buttons_by_species["decomposer"]
    y = sb.y
    sections.append(sb.finish())

    # --- "Grafikonok" szakasz ---
    sb = SectionBuilder("Grafikonok", y)
    GRAPH_H = 40
    graph_rect = pygame.Rect(x, sb.y, w, GRAPH_H)
    sb.custom(GraphPanel(graph_rect, draw_population_graph))
    sb.gap(GRAPH_H + 32)
    env_graph_rect = pygame.Rect(x, sb.y, w, GRAPH_H)
    sb.custom(GraphPanel(env_graph_rect, draw_environment_graph))
    sb.gap(GRAPH_H + 32)
    y = sb.y
    sections.append(sb.finish())

    inspector_top_nominal = y

    def layout_sections() -> int:
        """Ujraszamolja minden szakasz fejlecenek es widgetjeinek `y`
        pozíciojat: az osszecsukott szakaszok csak a fejlecukkel foglalnak
        helyet, az utanuk kovetkezo tartalom pedig felfele csuszik. A
        visszaadott ossz-eltolast a szekciok utani (nem szekcionalt)
        elemek (pl. az inspector) is felhasznaljak."""
        shift = 0
        for section in sections:
            header = section["header"]
            header.rect.y = section["top"] - shift
            if header.collapsed:
                shift += (section["bottom"] - section["top"]) - (BTN_H + GAP_HEADER_COLLAPSED)
            else:
                for widget, nominal_y in section["items"]:
                    widget.rect.y = nominal_y - shift
        return shift

    layout_sections()

    running = True
    while running:
        total_shift = layout_sections()
        inspector_top = inspector_top_nominal - total_shift
        # sose logjon tul az inspector a panel/ablak aljan - ha nagyon kicsi a
        # kepernyo, inkabb zsugorodjon (akar 0-ig), mint hogy kilogjon
        inspector_rect = pygame.Rect(x, inspector_top, w, max(0, config.WINDOW_HEIGHT - inspector_top - 15))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if analysis_window.visible and analysis_window.handle_event(event):
                continue

            handled = False
            for widget in always_widgets:
                if widget.handle_event(event):
                    handled = True

            if not handled:
                for section in sections:
                    if section["header"].handle_event(event):
                        handled = True

            if not handled:
                for section in sections:
                    if section["header"].collapsed:
                        continue
                    for widget, _ in section["items"]:
                        if widget.handle_event(event):
                            handled = True

            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx < config.SIM_WIDTH:
                    if analysis_window.visible and analysis_window.compare_picking is not None:
                        # DNS-osszehasonlitashoz a terkepen kivalasztott
                        # egyedet az "A" vagy "B" helyre allitja (lasd
                        # ui/analysis.py AnalysisWindow.assign_compare_entity)
                        analysis_window.assign_compare_entity(find_clicked_entity(sim, (mx, my)))
                    elif pending_spawn["species"] is not None:
                        # a lehelyezo mod aktiv marad, hogy tobb egyedet is le
                        # lehessen rakni egymas utan - ESC-cel, jobb kattintassal
                        # vagy uj eszkoz valasztasaval lehet kilepni belole
                        sim.spawn_entity(pending_spawn["species"], float(mx), float(my))
                    else:
                        select_entity(find_clicked_entity(sim, (mx, my)))
                else:
                    dns_rect = get_dns_line_rect(inspector_rect, sim.selected_entity)
                    if dns_rect is not None and dns_rect.collidepoint(mx, my):
                        inspector_state["dna_expanded"] = not inspector_state["dna_expanded"]

            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if pending_spawn["species"] is not None:
                    pending_spawn["species"] = None
                elif event.pos[0] < config.SIM_WIDTH:
                    select_entity(find_clicked_entity(sim, event.pos))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    toggle_pause()
                elif event.key == pygame.K_r:
                    do_reset()
                elif event.key == pygame.K_s:
                    do_step()
                elif event.key == pygame.K_ESCAPE:
                    pending_spawn["species"] = None

        if sim_is_running():
            # ha a szimulacio (ujra) fut, az elemzes ablak ertelmetlenne
            # valna (a nezet elavulna) - automatikusan eltunik
            analysis_window.close()
        analysis_button.toggled = analysis_window.visible

        sim.update(1.0)

        screen.fill(config.COLOR_BG)

        env_rgb = sim.environment.to_rgb_array(sim.weather, map_view_state["layer"])
        env_surface_small = pygame.surfarray.make_surface(env_rgb)
        env_surface = pygame.transform.scale(env_surface_small, (config.SIM_WIDTH, config.SIM_HEIGHT))
        screen.blit(env_surface, (0, 0))

        map_legend = sim.environment.get_layer_legend(map_view_state["layer"])
        if map_legend is not None:
            color_lo, color_hi, val_lo, val_hi, fmt = map_legend
            draw_map_legend(screen, font_small, (config.SIM_WIDTH - 70, 10), color_lo, color_hi, val_lo, val_hi, fmt)

        for plant in sim.plants:
            plant.draw(screen)
        for herbivore in sim.herbivores:
            herbivore.draw(screen)
        for carnivore in sim.carnivores:
            carnivore.draw(screen)
        for decomposer in sim.decomposers:
            decomposer.draw(screen)

        if analysis_window.visible:
            analysis_window.draw_world_markers(screen)
            analysis_window.draw_compare_markers(screen, font_small)

        if sim.selected_entity is not None:
            entity = sim.selected_entity
            radius = int(entity.traits.get("size", 5.0)) + 5
            pygame.draw.circle(screen, (255, 255, 255), (int(entity.x), int(entity.y)), radius, 2)

        if pending_spawn["species"] is not None:
            hint_text = f"Kattints a vilagra a lehelyezeshez ({pending_spawn['species']}) - ESC vagy jobb klikk: kilepes"
            hint_surf = font.render(hint_text, True, (255, 255, 255))
            screen.blit(hint_surf, (10, config.SIM_HEIGHT - 24))

        if analysis_window.visible and analysis_window.compare_picking is not None:
            compare_hint_text = f"DNS osszehasonlitas: kattints egy egyedre a terkepen ({analysis_window.compare_picking.upper()})"
            compare_hint_surf = font.render(compare_hint_text, True, (255, 255, 255))
            screen.blit(compare_hint_surf, (10, config.SIM_HEIGHT - 44))

        if not sim.started:
            edit_hint = font.render(
                "Szerkeszto mod: helyezz el egyedeket (a domborzat ujra is "
                "generalhato), majd inditsd a szimulaciot",
                True, (255, 255, 255),
            )
            screen.blit(edit_hint, (10, 64))

        draw_hud(screen, font, sim, clock.get_fps())

        pygame.draw.rect(screen, config.COLOR_PANEL, panel_rect)
        pygame.draw.line(screen, config.COLOR_PANEL_BORDER, (panel_x, 0), (panel_x, config.WINDOW_HEIGHT), 1)

        for widget in always_widgets:
            widget.draw(screen, font_small)

        for section in sections:
            section["header"].draw(screen, font_small)
            if not section["header"].collapsed:
                for widget, _ in section["items"]:
                    widget.draw(screen, font_small)

        draw_inspector(
            screen, inspector_rect, font_small, sim.selected_entity, inspector_state["dna_expanded"],
            environment=sim.environment, weather=sim.weather,
        )

        analysis_window.draw(screen, font, font_small)

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
