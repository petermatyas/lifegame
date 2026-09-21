"""Kozos allapot-cimkek minden entitas szamara (inspector/HUD megjelenites
es a rajzolashoz). Az `Entity.state` mezoje minden update()-kor ezekre az
ertekekre allitodik at, a ténylegesen vegrehajtott viselkedes alapjan."""

from __future__ import annotations

DEAD = "Halott"
WANDER = "Koborol"
HUNGRY = "Ehes"
EATING = "Eszik"
FLEEING = "Menekul"
HUNTING = "Vadaszik"
SEEKING_FOOD = "Taplalekot keres"
MATING = "Parosodik"
SLEEPING = "Alszik"
GROWING = "Novekszik"
WITHERING = "Hervad"
SEEDING = "Magot hint"
SEED = "Mag"
DECOMPOSING = "Bomlaszt"
