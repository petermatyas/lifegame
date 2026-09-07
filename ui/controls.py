"""Újrafelhasználható UI elemek: csúszka és gomb."""

from __future__ import annotations

from typing import Callable

import pygame

import config


class Slider:
    def __init__(
        self,
        rect: tuple[int, int, int, int],
        min_val: float,
        max_val: float,
        value: float,
        label: str,
        on_change: Callable[[float], None] | None = None,
        fmt: str = "{:.2f}",
    ):
        self.rect = pygame.Rect(rect)
        self.min_val = min_val
        self.max_val = max_val
        self.value = value
        self.label = label
        self.on_change = on_change
        self.fmt = fmt
        self.dragging = False

    def _handle_x(self) -> float:
        span = self.max_val - self.min_val
        t = 0.0 if span == 0 else (self.value - self.min_val) / span
        return self.rect.x + t * self.rect.width

    def _update_from_mouse(self, mouse_x: int) -> None:
        t = (mouse_x - self.rect.x) / self.rect.width
        t = max(0.0, min(1.0, t))
        self.value = self.min_val + t * (self.max_val - self.min_val)
        if self.on_change is not None:
            self.on_change(self.value)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit_rect = self.rect.inflate(4, 12)
            if hit_rect.collidepoint(event.pos):
                self.dragging = True
                self._update_from_mouse(event.pos[0])
                return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.dragging:
                self.dragging = False
                return True
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_from_mouse(event.pos[0])
            return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        pygame.draw.rect(surface, (55, 55, 68), self.rect, border_radius=4)
        span = self.max_val - self.min_val
        t = 0.0 if span == 0 else (self.value - self.min_val) / span
        fill_width = int(self.rect.width * max(0.0, min(1.0, t)))
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(surface, config.COLOR_ACCENT, fill_rect, border_radius=4)
        handle_x = int(self._handle_x())
        pygame.draw.circle(surface, (235, 235, 240), (handle_x, self.rect.centery), 7)

        label_surf = font.render(f"{self.label}: {self.fmt.format(self.value)}", True, config.COLOR_TEXT)
        surface.blit(label_surf, (self.rect.x, self.rect.y - 18))


class Button:
    def __init__(self, rect: tuple[int, int, int, int], text: str, on_click: Callable[[], None], toggled: bool = False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.on_click = on_click
        self.toggled = toggled

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.on_click()
            return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        color = config.COLOR_ACCENT if self.toggled else (55, 55, 68)
        pygame.draw.rect(surface, color, self.rect, border_radius=6)
        pygame.draw.rect(surface, config.COLOR_PANEL_BORDER, self.rect, 1, border_radius=6)
        text_surf = font.render(self.text, True, config.COLOR_TEXT)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))
