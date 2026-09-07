# Élet Szimuláció

Pygame alapú 2D élet-szimuláció: növények, növényevők és ragadozók élnek,
táplálkoznak, szaporodnak és halnak meg egy szabályozható környezetben
(hőmérséklet, víz, eső, nappal/éjszaka). Minden entitásnak van egy
DNS-szerű genetikai kódja, ami szaporodáskor (crossover + mutáció)
öröklődik és formálja az utódok tulajdonságait.

A tervdokumentum: [ELET_JATEK_TERV.md](ELET_JATEK_TERV.md)

## Telepítés

```
pip install -r requirements.txt
```

## Futtatás

```
python main.py
```

## Irányítás

- **SPACE** – szünet / folytatás
- **S** – egy lépés léptetése (szünet alatt hasznos)
- **R** – újraindítás új véletlen populációval
- **Bal kattintás a világon** – kiválasztott entitás adatainak (DNS-kód,
  tulajdonságok, energia) megjelenítése a jobb oldali panelen
- **"+ ... lehelyezése" gombok** – új növény/növényevő/ragadozó
  elhelyezése kattintással a világ tetszőleges pontján (ESC törli)
- **Jobb oldali csúszkák** – időskálázás, alap hőmérséklet, eső esélye
  és intenzitása, mutációs ráta és erősség élőben állítható
- **"Eső: Automata / Kényszerítve BE / KI" gomb** – manuálisan
  felülbírálható az automata időjárás

## Felépítés

```
config.py            - alapértelmezett paraméterek, gén-tartományok
entities/
  genome.py           - DNS-szerű genom: crossover, mutáció, dekódolás
  base.py, mobile.py   - közös entitás-logika
  plant.py             - fotoszintézis, magszórás
  herbivore.py          - táplálkozás, menekülés, szaporodás
  carnivore.py          - vadászat, szaporodás
world/
  environment.py       - hőmérséklet/víz rács (NumPy), diffúzió
  weather.py            - nappal/éjszaka, eső/szárazság ciklus
  grid.py               - térbeli hash a gyors szomszéd-kereséshez
simulation/
  engine.py             - fő update-ciklus, szaporodás, spawnolás
  stats.py              - populáció-történet a grafikonhoz
ui/
  controls.py           - csúszka és gomb widgetek
  hud.py                 - HUD szövegek, populáció-grafikon
  inspector.py           - kattintható entitás-részletező
main.py                 - game loop, ablak, esemény-kezelés
```

Az alap paraméterek (metabolizmus, harapásméret, ragadozási siker, stb.)
úgy vannak hangolva, hogy tartós, oszcilláló ("boom-bust") populáció-
dinamika alakuljon ki teljes kihalás nélkül – egy kis beépített
"vándorlás" mechanizmus (`Simulation._handle_migration`) akadályozza meg,
hogy egy faj véglegesen kihaljon egy rossz ciklus után.
