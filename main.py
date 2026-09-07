"""Elet Szimulacio - belepesi pont.

Iranyitas:
  SPACE - szunet/folytatas
  S     - egy lepes (szunet alatt)
  R     - ujrainditas
  Egeret kattintva a vilagra: entitas kivalasztasa, vagy uj egyed
  lehelyezese, ha eppen aktiv egy "+ ... lehelyezese" gomb.
"""

from __future__ import annotations

import sys

import pygame

import config
from simulation.engine import Simulation
from ui.controls import Slider, Button
from ui.hud import draw_hud, draw_population_graph, draw_environment_graph
from ui.inspector import find_clicked_entity, draw_inspector


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Elet Szimulacio")
    screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 14)
    font_small = pygame.font.SysFont("consolas", 12)

    sim = Simulation()

    panel_x = config.SIM_WIDTH
    panel_rect = pygame.Rect(panel_x, 0, config.PANEL_WIDTH, config.WINDOW_HEIGHT)

    pending_spawn: dict[str, str | None] = {"species": None}

    def set_pending(species: str) -> None:
        pending_spawn["species"] = species

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
    y = 40

    pause_button = Button((x, y, w // 2 - 5, 28), "Szunet", toggle_pause)
    step_button = Button((x + w // 2 + 5, y, w // 2 - 5, 28), "Lepes", do_step)
    y += 34
    reset_button = Button((x, y, w, 28), "Ujrainditas (R)", do_reset)
    y += 52

    speed_slider = Slider(
        (x, y, w, 10), 0.1, 8.0, sim.weather.time_scale, "Sebesseg",
        on_change=lambda v: setattr(sim.weather, "time_scale", v), fmt="{:.1f}x",
    )
    y += 34

    temp_slider = Slider(
        (x, y, w, 10), -10.0, 40.0, sim.weather.base_temperature, "Alaphomerseklet",
        on_change=lambda v: setattr(sim.weather, "base_temperature", v), fmt="{:.0f} C",
    )
    y += 34

    rain_chance_slider = Slider(
        (x, y, w, 10), 0.0, 0.01, sim.weather.rain_chance_per_tick, "Eso eselye",
        on_change=lambda v: setattr(sim.weather, "rain_chance_per_tick", v), fmt="{:.4f}",
    )
    y += 34

    rain_intensity_slider = Slider(
        (x, y, w, 10), 0.0, 3.0, sim.weather.rain_intensity, "Eso intenzitasa",
        on_change=lambda v: setattr(sim.weather, "rain_intensity", v), fmt="{:.2f}",
    )
    y += 34

    rain_button = Button((x, y, w, 26), "Eso: Automata", cycle_rain)
    y += 50

    mutation_rate_slider = Slider(
        (x, y, w, 10), 0.0, 0.3, sim.mutation_rate, "Mutacio rata",
        on_change=lambda v: setattr(sim, "mutation_rate", v), fmt="{:.2f}",
    )
    y += 34

    mutation_strength_slider = Slider(
        (x, y, w, 10), 0.0, 0.5, sim.mutation_strength, "Mutacio erosseg",
        on_change=lambda v: setattr(sim, "mutation_strength", v), fmt="{:.2f}",
    )
    y += 38

    spawn_label_y = y
    y += 18
    spawn_plant_btn = Button((x, y, w, 26), "+ Noveny lehelyezese", lambda: set_pending("plant"))
    y += 30
    spawn_herb_btn = Button((x, y, w, 26), "+ Novenyevo lehelyezese", lambda: set_pending("herbivore"))
    y += 30
    spawn_carn_btn = Button((x, y, w, 26), "+ Ragadozo lehelyezese", lambda: set_pending("carnivore"))
    y += 32

    graph_rect = pygame.Rect(x, y + 18, w, 100)
    y += 18 + 100 + 40

    env_graph_rect = pygame.Rect(x, y + 18, w, 100)
    y += 18 + 100 + 40

    inspector_rect = pygame.Rect(x, y, w, config.WINDOW_HEIGHT - y - 15)

    buttons = [
        pause_button, step_button, reset_button, rain_button,
        spawn_plant_btn, spawn_herb_btn, spawn_carn_btn,
    ]
    sliders = [
        speed_slider, temp_slider, rain_chance_slider, rain_intensity_slider,
        mutation_rate_slider, mutation_strength_slider,
    ]

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            handled = False
            for slider in sliders:
                if slider.handle_event(event):
                    handled = True

            if not handled:
                for button in buttons:
                    if button.handle_event(event):
                        handled = True

            if not handled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if mx < config.SIM_WIDTH:
                    if pending_spawn["species"] is not None:
                        sim.spawn_entity(pending_spawn["species"], float(mx), float(my))
                        pending_spawn["species"] = None
                    else:
                        sim.selected_entity = find_clicked_entity(sim, (mx, my))

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    toggle_pause()
                elif event.key == pygame.K_r:
                    do_reset()
                elif event.key == pygame.K_s:
                    do_step()
                elif event.key == pygame.K_ESCAPE:
                    pending_spawn["species"] = None

        sim.update(1.0)

        screen.fill(config.COLOR_BG)

        env_rgb = sim.environment.to_rgb_array(sim.weather)
        env_surface_small = pygame.surfarray.make_surface(env_rgb)
        env_surface = pygame.transform.scale(env_surface_small, (config.SIM_WIDTH, config.SIM_HEIGHT))
        screen.blit(env_surface, (0, 0))

        for plant in sim.plants:
            plant.draw(screen)
        for herbivore in sim.herbivores:
            herbivore.draw(screen)
        for carnivore in sim.carnivores:
            carnivore.draw(screen)

        if sim.selected_entity is not None and not sim.selected_entity.is_dead():
            entity = sim.selected_entity
            radius = int(entity.traits.get("size", 5.0)) + 5
            pygame.draw.circle(screen, (255, 255, 255), (int(entity.x), int(entity.y)), radius, 2)

        if pending_spawn["species"] is not None:
            hint_text = f"Kattints a vilagra a lehelyezeshez ({pending_spawn['species']}) - ESC: megse"
            hint_surf = font.render(hint_text, True, (255, 255, 255))
            screen.blit(hint_surf, (10, config.SIM_HEIGHT - 24))

        draw_hud(screen, font, sim, clock.get_fps())

        pygame.draw.rect(screen, config.COLOR_PANEL, panel_rect)
        pygame.draw.line(screen, config.COLOR_PANEL_BORDER, (panel_x, 0), (panel_x, config.WINDOW_HEIGHT), 1)

        for slider in sliders:
            slider.draw(screen, font_small)
        for button in buttons:
            button.draw(screen, font_small)

        spawn_label = font_small.render("Uj egyed elhelyezese:", True, config.COLOR_TEXT_DIM)
        screen.blit(spawn_label, (x, spawn_label_y))

        draw_population_graph(screen, graph_rect, font_small, sim.stats)
        draw_environment_graph(screen, env_graph_rect, font_small, sim.stats)
        draw_inspector(screen, inspector_rect, font_small, sim.selected_entity)

        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
