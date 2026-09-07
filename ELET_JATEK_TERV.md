# Élet Szimuláció – Tervdokumentum

Pygame alapú 2D élet-szimulációs "sandbox" játék, ahol növények, növényevők és
ragadozók populációi élnek, szaporodnak és fejlődnek (genetikai öröklődéssel),
miközben egy szabályozható környezet (hőmérséklet, víz, eső, nappal/éjszaka)
hat rájuk.

## 1. Célok és alapelvek

- **Emergens viselkedés**: nincs központi "AI szkript" fajonként, hanem
  egyszerű szabályok + genetikailag öröklődő tulajdonságok hoznak létre
  komplex, kiszámíthatatlan populációdinamikát (Conway's Game of Life
  szellemében, de ágens-alapú, folytonos tulajdonságokkal).
- **Konfigurálhatóság**: minden entitás tulajdonsága (sebesség, méret,
  energiaigény, stb.) paraméterezhető, és minden környezeti paraméter kézzel
  vagy automata módban is vezérelhető.
- **Megfigyelhetőség**: a felhasználó lásson statisztikákat (populáció,
  átlagos tulajdonságok generációnként), és tudjon rákattintani egyedi
  entitásokra a DNS-ük megtekintéséhez.
- **Fokozatos építés**: a terv fázisokra bontva, minden fázis után futtatható,
  látható eredménnyel.

## 2. Technológiai stack

- **Python 3.11+**
- **Pygame-ce** (vagy `pygame`) – renderelés, input, game loop
- **NumPy** – rácsalapú környezeti mezők (hőmérséklet/víz térkép), gyors
  vektorizált entitás-számítások nagy populáció esetén
- Opcionális: **matplotlib** vagy saját Pygame-es grafikon a populáció
  statisztikák megjelenítésére (hogy ne kelljen külön ablakot nyitni,
  inkább egy beépített mini-grafikon panel)

## 3. Fájlstruktúra

```
life/
├── main.py                  # belépési pont, game loop
├── config.py                # alap konstansok, defaultok
├── world/
│   ├── environment.py       # környezeti rács: hőmérséklet, víz, fény
│   ├── weather.py           # eső/szárazság ciklusok, napszak
│   └── grid.py              # térbeli particionálás (szomszéd-keresés gyorsítása)
├── entities/
│   ├── base.py              # Entity absztrakt osztály
│   ├── genome.py            # DNS kódolás, crossover, mutáció
│   ├── plant.py             # Plant osztály
│   ├── herbivore.py         # Herbivore osztály
│   └── carnivore.py         # Carnivore osztály
├── simulation/
│   ├── engine.py            # update ciklus, ütközésvizsgálat, populáció-kezelés
│   └── stats.py             # metrikák gyűjtése (populáció, generációk, átlagok)
├── ui/
│   ├── hud.py                # felső/oldalsó info panel
│   ├── controls.py           # csúszkák, gombok a paraméterekhez
│   └── inspector.py          # kattintásra megjelenő entitás-részletező
└── assets/                   # opcionális textúrák/ikonok (kezdetben egyszerű
                               # színes körök/alakzatok is elegendőek)
```

## 4. Entitás rendszer

### 4.1 Bázis osztály (`Entity`)

Minden entitás közös tulajdonságai:

| Tulajdonság        | Leírás                                             |
|--------------------|-----------------------------------------------------|
| `position`         | (x, y) a világban                                   |
| `energy`           | jelenlegi energiaszint (0 → halál)                  |
| `age`              | életkor (tick-ekben)                                |
| `genome`           | a DNS-kód objektuma (lásd 5. fejezet)               |
| `size`             | fizikai méret (mozgás sebességét, energiaigényt,     |
|                    | ragadozó/zsákmány viszonyt is befolyásolja)          |
| `max_energy`       | energiakapacitás                                    |
| `metabolism_rate`  | mennyi energiát fogyaszt időegységenként             |
| `speed`            | mozgási sebesség                                    |
| `vision_range`     | milyen távolságról érzékel más entitásokat/erőforrást|
| `fertility`        | szaporodási hajlam/gyakoriság                        |
| `lifespan`         | maximális életkor (öregségi halál)                   |
| `temp_tolerance`   | (min, max, optimum) hőmérséklet-tűrés                |
| `water_need`       | mennyi vízre van szüksége túléléshez                 |

Közös metódusok: `update(dt, environment)`, `is_dead()`, `try_reproduce(partner)`,
`draw(surface)`.

### 4.2 Növény (`Plant`)

- Nem mozog, gyökeret ver egy helyhez.
- Energiát nem táplálkozással, hanem **fotoszintézissel** nyer: a helyi
  hőmérséklet, vízszint és nappal/éjszaka fény-értéke alapján (pl.
  `growth = f(sunlight, water, temp)` – egy haranggörbe-szerű optimum-függvény
  fajra jellemző optimum körül).
- Extra tulajdonságok: `growth_rate`, `seed_spread_radius` (mag szórási
  távolság), `drought_resistance`.
- Szaporodás: ha elég energiája van, "magot" hint egy közeli szabad
  cellába (aszexuális, enyhe mutációval), vagy két közeli növény
  "beporzással" (szexuális, DNS-keveréssel), ha a fajváltozat ezt engedi.
- Halál: vízhiány, extrém hőmérséklet, vagy megeszik (növényevő).

### 4.3 Növényevő (`Herbivore`)

- Mozog, keresi a legközelebbi növényt `vision_range`-en belül.
- Táplálkozás: ha elég közel ér egy növényhez, energiát von el belőle
  (részben vagy teljesen elfogyasztja).
- Extra tulajdonságok: `bite_size` (mennyit tud enni egyszerre),
  `flee_speed_bonus` (ragadozó elől menekülésnél), `herd_instinct`
  (csordaösztön – opcionális, közösségi viselkedéshez).
- Viselkedés-állapotgép: `WANDER → SEEK_FOOD → EAT`, illetve
  `FLEE` ha ragadozó a látótávolságban, `SEEK_MATE` ha elég energiája van.
- Halál: éhezés (energia 0), ragadozó megeszi, extrém környezeti hatás,
  öregség.

### 4.4 Ragadozó (`Carnivore`)

- Mozog, keresi a legközelebbi növényevőt (vagy gyengébb ragadozót, ha
  kannibál/omnivor variánst is akarunk engedni – opcionális kiterjesztés).
- Extra tulajdonságok: `attack_power`, `hunt_success_rate` (befolyásolja
  a `size`, `speed`, zsákmány `defense`/`flee_speed` viszonya),
  `pack_hunting` (opcionális csoportos vadászat).
- Táplálkozás/vadászat: sikeres "elkapás" esetén a zsákmány energiájának
  egy részét megszerzi; sikertelen vadászat energiát fogyaszt eredmény
  nélkül (kockázat/nyereség egyensúly).
- Halál: éhezés, öregség, extrém környezet (ragadozóknak nincs
  természetes ellensége a v1-ben, de túlszaporodás → éhínség
  önszabályozó visszacsatolás).

### 4.5 Interakciós mátrix

| Ki hat kire        | Hatás                                                        |
|--------------------|---------------------------------------------------------------|
| Környezet → Növény | növekedés/hervadás sebessége                                   |
| Növény → Növényevő | táplálékforrás (energia)                                       |
| Növényevő → Növény | fogyasztás (populáció-visszaszorítás)                          |
| Növényevő → Ragadozó | táplálékforrás (energia)                                     |
| Ragadozó → Növényevő | predáció (populáció-visszaszorítás), menekülési viselkedés   |
| Környezet → Növényevő/Ragadozó | metabolizmus-sebesség, mozgássebesség, halálozás    |
| Azonos faj egyedei → egymás | szaporodás (ha közel vannak és mindkettőnek elég energiája van) |
| Sűrűség → mindegyik | túlnépesedés esetén erőforrás-verseny (implicit, a közös        |
|                    | táplálékkészleten keresztül, nem külön szabály)                |

## 5. DNS-szerű genetikai kód

### 5.1 Reprezentáció

A genom egy fix hosszúságú **gén-tömb** (nem szöveges DNS-string, hanem
lebegőpontos/normalizált értékek tömbje – könnyebben kombinálható és
mutálható, de megjeleníthető szöveges "kód" formában is, pl. hex-string,
a UI-on való megjelenítéshez).

```python
GENE_LAYOUT = [
    "speed", "size", "vision_range", "metabolism_rate",
    "max_energy", "fertility", "lifespan",
    "temp_tolerance_min", "temp_tolerance_max",
    "water_need", "attack_power", "defense",
    "camouflage", "diet_bias",   # diet_bias csak omnivor kiterjesztésnél kell
]

class Genome:
    genes: dict[str, float]   # minden érték 0.0–1.0 normalizált

    def to_phenotype(self) -> dict:
        """Normalizált génekből tényleges (skálázott) tulajdonságokat számol,
        fajspecifikus min/max határok alapján."""

    def to_code_string(self) -> str:
        """Emberi/UI-barát megjelenítés, pl. 16 gén → 16 hexa karakter."""
```

- A gének **normalizált [0,1] tartományban** tárolódnak, a fenotípusba
  alakításkor faj-specifikus (`Plant`/`Herbivore`/`Carnivore`) min-max
  skálázás történik (pl. `speed_gene * (max_speed - min_speed) + min_speed`).
- Ez lehetővé teszi, hogy egyazon crossover/mutáció logika működjön minden
  fajon, csak a dekódolási skála más.

### 5.2 Szaporodás / Crossover

```python
def crossover(genome_a: Genome, genome_b: Genome) -> Genome:
    child_genes = {}
    for gene_name in GENE_LAYOUT:
        # egyenletes crossover: génenként véletlen melyik szülőtől örökli
        child_genes[gene_name] = random.choice(
            [genome_a.genes[gene_name], genome_b.genes[gene_name]]
        )
        # vagy: átlagolás enyhe szórással a folytonos jellegű tulajdonságoknál
    return Genome(child_genes).mutate()
```

- **Ivaros szaporodás** (növényevők, ragadozók, és opcionálisan a
  növények egy része): két szülő génjei génenként keverednek
  (uniform crossover vagy blend crossover).
- **Aszexuális szaporodás** (alap növény-mód): a szülő genomja
  másolódik, majd mutáció.

### 5.3 Mutáció

```python
def mutate(genome: Genome, mutation_rate=0.05, mutation_strength=0.1) -> Genome:
    for gene_name in genome.genes:
        if random.random() < mutation_rate:
            delta = random.uniform(-mutation_strength, mutation_strength)
            genome.genes[gene_name] = clamp(genome.genes[gene_name] + delta, 0, 1)
    return genome
```

- `mutation_rate` és `mutation_strength` globális szimulációs paraméterek,
  a UI-ból állíthatók (gyorsabb/lassabb evolúció demonstrálásához).

### 5.4 Kezdeti populáció

- A világ indulásakor minden fajhoz megadható egy **alap génkészlet**
  (defaultok `config.py`-ban), amely köré a kezdeti egyedek génjei kis
  véletlen szórással generálódnak – így azonnal van genetikai
  diverzitás, amiből a szelekció dolgozhat.

## 6. Környezeti rendszer

### 6.1 Térbeli reprezentáció

- A világ egy **rács** (pl. 64×48 cella), minden cellához tartozik:
  `temperature`, `water_level`, `sunlight` (nappal/éjszaka + felhőzet
  alapján). Az entitások folytonos (x, y) koordinátán mozognak, de a
  cella-értékeket a pozíciójuk alapján olvassák ki (bilineáris
  interpolációval a simább átmenetért).
- NumPy 2D tömbök a gyors frissítéshez; a hőmérséklet/víz terjedhet a
  szomszédos cellák között is (egyszerű diffúziós lépés minden tick-en),
  hogy ne legyenek éles, mesterséges határok.

### 6.2 Paraméterek

| Paraméter        | Hatás                                                                 |
|-------------------|------------------------------------------------------------------------|
| **Hőmérséklet**   | Minden entitásnak van `temp_tolerance` sávja; ezen kívül energia-      |
|                   | vesztés/sebesség-csökkenés/halálozási esély nő. Növényeknél a          |
|                   | növekedési görbét módosítja.                                          |
| **Víz**           | Cellánkénti víztartalom; növények növekedéséhez kell, növényevők/      |
|                   | ragadozók is elfogyaszthatják (csökkenti szomjúság-számlálójukat).     |
| **Eső**           | Időszakos esemény, ami feltölti a víz-rácsot és hőmérsékletet enyhén  |
|                   | csökkenti; vezérelhető gyakoriság/intenzitás csúszkával.               |
| **Szárazság**     | Elhúzódó eső nélküli időszak: a víz-rács fokozatosan csökken,          |
|                   | fokozott stresszt okoz minden fajnak.                                  |
| **Nappal/éjszaka**| Ciklikus fény-érték (szinusz görbe); befolyásolja a fotoszintézist,    |
|                   | egyes fajok éjszaka lassabbak/rejtettebbek (`camouflage` gén relevánsabbá|
|                   | válik éjszaka pl. ragadozóknál).                                       |

### 6.3 Vezérlés

- **Manuális mód**: csúszkák a UI-on (hőmérséklet alapszint, víz
  utánpótlás, eső valószínűség/erősség, nappal-éjszaka ciklus hossza és
  be/kikapcsolása).
- **Automata mód**: beépített szezonális ciklus (pl. szinuszos évszak-
  szimuláció), amit a manuális csúszkák felülírhatnak.
- **Idő kontroll**: play/pause, sebesség-szorzó (0.5x–10x), "step"
  (egy tick léptetése pause alatt), reset gomb új véletlen populációval.

## 7. Szimulációs ciklus (fő update sorrend)

```
1. Idő előrehaladtatása (ha nincs pause), day/night fázis frissítése
2. Környezeti rács frissítése (eső esemény, diffúzió, szárazság csökkenés)
3. Térbeli particionálás frissítése (grid/quadtree a szomszéd-kereséshez)
4. Minden Plant.update()  → fotoszintézis, növekedés, esetleges magszórás
5. Minden Herbivore.update() → érzékelés, mozgás, evés, menekülés, szaporodás
6. Minden Carnivore.update() → érzékelés, mozgás, vadászat, szaporodás
7. Halott entitások eltávolítása, új entitások (utódok) hozzáadása
8. Statisztikák frissítése (populáció-számláló, átlagos gén-értékek)
9. Renderelés (világ + entitások + HUD + UI panel)
```

Nagy populációnál a 3. lépés (térbeli particionálás, pl. egyszerű
rács-alapú "spatial hashing") kritikus a teljesítményhez, hogy az
"legközelebbi étel/zsákmány/ragadozó" keresés ne legyen O(n²).

## 8. UI / Vezérlőpanel

- **HUD**: aktuális idő (nap/óra), populációszámok fajonként, FPS.
- **Környezeti csúszkák**: hőmérséklet, víz utánpótlás, eső
  gyakoriság/erősség, nappal-éjszaka ciklus hossza, mutációs ráta.
- **Idő vezérlők**: pause/play, sebesség (1x/2x/5x/10x), step, reset.
- **Entitás inspector**: kattintásra kiválasztott egyed adatai
  (tulajdonságok, energia, kor, DNS kód string, szülők generációja).
- **Statisztika panel**: egyszerű vonaldiagram(ok) a populáció
  alakulásáról időben (Pygame-mel rajzolt polyline, nem kell külön lib).
- **Spawn eszköz**: kattintással/gombbal új entitás (adott fajú,
  testreszabható kezdő génekkel) helyezhető el a világba tesztelés
  céljából.

## 9. Fejlesztési fázisok (milestone-ok)

1. **Váz**: Pygame ablak, game loop, statikus rács megjelenítése,
   FPS-korlátozás.
2. **Környezet**: hőmérséklet/víz rács, nappal-éjszaka ciklus,
   vizuális megjelenítés (pl. rács színezése hőtérképként), eső effekt.
3. **Növények**: `Plant` osztály, fotoszintézis-alapú növekedés,
   halál/szaporodás, alap genom nélkül (fix tulajdonságokkal).
4. **Genom rendszer**: `Genome` osztály bevezetése a növényekhez,
   mutáció + aszexuális öröklődés tesztelése (fenotípus-eltolódás
   megfigyelése generációkon át).
5. **Növényevők**: mozgás, érzékelés, táplálkozás, energia-menedzsment,
   ivaros szaporodás + crossover.
6. **Ragadozók**: vadászat, predáció, populáció-egyensúly tesztelése
   (klasszikus Lotka–Volterra-szerű oszcilláció megfigyelése).
7. **UI vezérlők**: csúszkák a környezeti paraméterekhez, idő-vezérlés,
   spawn eszköz.
8. **Inspector + statisztikák**: kattintható entitás-részletező,
   populáció-grafikonok.
9. **Finomhangolás / egyensúlyozás**: alap paraméterek (metabolizmus,
   energiaértékek, mutációs ráta) hangolása, hogy a szimuláció hosszú
   távon se ne haljon ki azonnal, se ne robbanjon túlnépesedésbe.
10. **Polish / opcionális bővítések** (lásd 10. fejezet).

## 10. Lehetséges jövőbeli bővítések

- Fajok közötti hibridizáció-korlátozás (csak elég "hasonló" genomú
  egyedek szaporodhassanak egymással → fajképződés szimulálása).
- Terep-akadályok (hegyek, vízfelületek), amik korlátozzák a mozgást.
- Ökológiai fülkék: omnivor faj, dögevő (elhullott tetemekből táplálkozó)
  viselkedés.
- Mentés/betöltés (világ állapot + populáció szerializálása JSON-be).
- Genealógiai fa / leszármazási vizualizáció egy kiválasztott egyedre.
- Klimatikus események (hosszabb aszályos vagy hideg periódusok, mint
  "kihalási események").

## 11. Kockázatok / figyelendő pontok

- **Teljesítmény**: sok entitás (>1000) esetén a szomszéd-keresést és a
  rajzolást optimalizálni kell (spatial hashing, batch rendering).
- **Egyensúlyozás**: rosszul hangolt paraméterekkel a szimuláció könnyen
  egy fajra "összeomolhat" (mindenki kihal, vagy egy faj mindent
  ellep) – ezt kell interaktívan hangolhatóvá tenni, hogy a felhasználó
  is kísérletezhessen vele.
- **Determinizmus vs. változatosság**: érdemes egy globális seed opciót
  bevezetni a reprodukálható futtatásokhoz (debug/demo célra).
