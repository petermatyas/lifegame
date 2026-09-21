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
│   ├── environment.py       # környezeti rács: domborzat, hőmérséklet, víz, fény
│   ├── weather.py           # eső/szárazság ciklusok, napszak
│   └── grid.py              # térbeli particionálás (szomszéd-keresés gyorsítása)
├── entities/
│   ├── base.py              # Entity absztrakt osztály
│   ├── genome.py            # DNS kódolás, crossover, mutáció
│   ├── plant.py             # Plant osztály
│   ├── herbivore.py         # Herbivore osztály
│   ├── carnivore.py         # Carnivore osztály
│   └── decomposer.py        # Decomposer osztály (lebontó szervezet)
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
| `vision_range`     | érzékelési sugár: milyen távolságból méri fel a       |
|                    | környezetét (más entitások, erőforrások, helyi        |
|                    | környezeti értékek) – a genom szabályozza, minden      |
|                    | fajnál (mozgónál és helyhez kötöttnél is) létezik      |
| `fertility`        | szaporodási hajlam/gyakoriság                        |
| `lifespan`         | maximális életkor (öregségi halál)                   |
| `temp_tolerance`   | (min, max, optimum) hőmérséklet-tűrés                |
| `water_need`       | mennyi vízre van szüksége túléléshez                 |
| `state`            | aktuális viselkedés-állapot (pl. Éhes, Alszik,        |
|                    | Menekül, Halott, stb.) – minden `update()`-kor        |
|                    | frissül, lásd 4.7. Állapotok                          |

Közös metódusok: `update(dt, environment)`, `is_dead()`, `try_reproduce(partner)`,
`draw(surface)`.

A `vision_range` minden fajnál genetikailag kódolt (lásd 5. fejezet,
`GENE_LAYOUT`), így egyedenként és generációnként eltérhet, és a
szelekció is alakíthatja (pl. jobb érzékelés → hatékonyabb táplálékkeresés,
de nagyobb érzékelési sugár esetleg nagyobb energiaigénnyel jár). Mozgó
fajoknál (Herbivore, Carnivore, lassan a Decomposer is) ez a távolság
szabja meg, honnan vesznek észre táplálékot/veszélyt; helyhez kötött
fajoknál (Plant) a közvetlen szomszédos cellák állapotát (pl. zsúfoltság,
talajminőség) méri fel ugyanez a sugár.

### 4.2 Növény (`Plant`)

- Nem mozog, gyökeret ver egy helyhez.
- Energiát nem táplálkozással, hanem **fotoszintézissel** nyer: a helyi
  hőmérséklet, vízszint és nappal/éjszaka fény-értéke alapján (pl.
  `growth = f(sunlight, water, temp, humus)` – egy haranggörbe-szerű
  optimum-függvény fajra jellemző optimum körül, ahol a helyi
  `humus_level` egy szorzó/kiegészítő tápanyag-tag a fotoszintézis
  mellett).
- Extra tulajdonságok: `growth_rate`, `seed_spread_radius` (mag szórási
  távolság), `drought_resistance`.
- **`water_tolerance` gén** (0–1, DNS-ben kódolva, lásd 5.1): azt szabja
  meg, mennyire bírja a *túl sok/állandó* vizet (elárasztott talaj,
  tó/tenger feneke – lásd 6.2). Egy `flood_stress` érték méri, mekkora a
  "vízfelesleg" a növény `water_need`-jéhez képest, szorozva
  `(1 - water_tolerance)`-vel:
  - Alacsony `water_tolerance` (**szárazságkedvelő** típus): állóvízben
    vagy tartósan túl nedves talajon visszaesik a növekedése, súlyos
    esetben fokozatosan **elrohad** (`Hervad` állapot, energia-vesztés
    arányos a `flood_stress` mértékével – minél rosszabb az arány,
    *annál rövidebb ideig* bírja).
  - Magas `water_tolerance` (**vízinövény** típus): a `flood_stress`
    gyakorlatilag nulla, tehát korlátlanul megél állóvízben is – sőt,
    mivel ott a vízszint mindig maximális, sosem szenved szárazságtól.
  - A `water_tolerance` génje alapján (a többi fajtól eltérően) a növény
    magszórása/kezdeti elhelyezése **nem kerüli az állóvíz-cellákat**
    (csak a sziklás akadályokat) – a tényleges túlélést a fenti
    mechanizmus dönti el, nem egy előre beépített tiltás. Így a
    populációból generációk alatt természetes szelekcióval alakulhatnak
    ki tisztán szárazságkedvelő és tisztán vízi altípusok.
  - **Kezdeti víztűrő képesség**: a szerkesztő módban (lásd 6.5) egy
    "Kezdő víztűrő képesség" csúszka állítja be, hogy az induláskor
    (kézzel/automatikusan) létrehozott növények genomjában milyen érték
    körül szóródjon a `water_tolerance` gén – 0 felé húzva induláskor
    inkább szárazságkedvelő, 1 felé húzva inkább vízkedvelő populáció
    indul, 0.5-nél pedig (az alapértelmezett) teljesen vegyes/véletlen.
- A `vision_range` génje alapján méri fel a közvetlen környezetét: a
  hatósugarán belüli cellák humusz-/vízszintjét és a szomszédos növények
  sűrűségét (zsúfoltság), ami befolyásolja, hova érdemes magot szórnia.
- Szaporodás: ha elég energiája van, "magot" hint egy közeli szabad
  cellába (aszexuális, enyhe mutációval), vagy két közeli növény
  "beporzással" (szexuális, DNS-keveréssel), ha a fajváltozat ezt engedi.
- Állapotai (lásd 4.7): `Növekszik` (alapértelmezett), `Hervad` (szélsőséges
  hőmérséklet/tartós vízhiány/tartós elárasztás esetén), `Magot hint` (a szaporodás
  pillanatában).
- Halál: vízhiány, extrém hőmérséklet, vagy megeszik (növényevő).

### 4.3 Növényevő (`Herbivore`)

- Mozog, keresi a legközelebbi növényt `vision_range`-en belül.
- Táplálkozás: ha elég közel ér egy növényhez, energiát von el belőle
  (részben vagy teljesen elfogyasztja).
- Extra tulajdonságok: `bite_size` (mennyit tud enni egyszerre),
  `flee_speed_bonus` (ragadozó elől menekülésnél), `herd_instinct`
  (csordaösztön – opcionális, közösségi viselkedéshez).
- Állapotai (lásd 4.7): `Menekül` (ragadozó a látótávolságban) > `Éhes`
  (alacsony energiaszint) > `Eszik` / `Táplálékot keres` (növényt talált,
  eszi vagy felé mozog) > `Párosodik` > `Alszik` (éjszaka, ha nincs
  sürgető szükséglet) > `Kóborol` (alapértelmezett).
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
- Állapotai (lásd 4.7): `Vadászik` (zsákmányt üldöz/támad) > `Eszik`
  (sikeres elkapás után táplálkozik) > `Éhes` > `Párosodik` > `Alszik`
  (éjszaka, ha nincs zsákmány a közelben) > `Kóborol`.
- Halál: éhezés, öregség, extrém környezet (ragadozóknak nincs
  természetes ellensége a v1-ben, de túlszaporodás → éhínség
  önszabályozó visszacsatolás).

### 4.5 Lebontó szervezet (`Decomposer`)

- Nagyon lassan mozog (a `speed` génje a fajok közül a legalacsonyabb
  tartományba van skálázva – mint egy csigatempójú, kúszó/terjedő
  szervezet, pl. rothasztó gomba vagy féreg), és nem vadászik: a
  közelében lévő elhullott állatokat és elpusztult növényi maradványokat
  bontja le **humusszá**.
- Amikor egy entitás elpusztul, a helyén létrejön egy **detritus**
  (szerves törmelék) objektum, ami az elhunyt energiájának egy részét
  hordozza. A lebontók a `vision_range`-ükön belüli detritus felé lassan
  odavonszolják magukat, majd fogyasztják azt – ez az ő
  táplálékforrásuk, nem a fotoszintézis és nem is élő zsákmány.
- Extra tulajdonságok: `decomposition_rate` (mennyi detritust bont le
  időegységenként – fajváltozatonként eltérő: van gyors, "opportunista"
  és lassú, "alapos" lebontó típus is), `humus_yield` (mennyi humuszt
  termel egységnyi elbontott anyagból), `spread_radius` (spórázási/
  terjeszkedési távolság új lebontó-telepekhez, a lassú mozgás mellett
  ez a fő terjeszkedési mód).
- A lebontás mellékterméke a **humusz**, ami visszakerül a környezeti
  rácsba (lásd 6. fejezet, `humus_level` mező), és a növények ezt
  tápanyagként hasznosítják a növekedésükhöz a fotoszintézis mellett –
  humuszban gazdag talajon gyorsabban/erősebben nőnek.
- Állapotai (lásd 4.7): `Bomlaszt` (detritust fogyaszt) > `Éhes` /
  `Táplálékot keres` (detritus felé mozog vagy nincs elérhető) > `Párosodik`
  > `Alszik` (éjszaka) > `Kóborol`.
- Halál: elfogy a környékén elérhető detritus (nincs mit lebontani),
  vagy szélsőséges környezet (pl. túl száraz/fagyos talaj gátolja a
  lebontó szervezeteket).

### 4.6 Interakciós mátrix

| Ki hat kire        | Hatás                                                        |
|--------------------|---------------------------------------------------------------|
| Környezet → Növény | növekedés/hervadás sebessége                                   |
| Növény → Növényevő | táplálékforrás (energia)                                       |
| Növényevő → Növény | fogyasztás (populáció-visszaszorítás)                          |
| Növényevő → Ragadozó | táplálékforrás (energia)                                     |
| Ragadozó → Növényevő | predáció (populáció-visszaszorítás), menekülési viselkedés   |
| Elhullott állat/növény → Lebontó | táplálékforrás (detritus-energia), eltérő ütemben       |
|                    | fajtánként (`decomposition_rate`)                              |
| Lebontó → Humusz (környezet) | humusztermelés (`humus_yield`) a helyi rácscellába    |
| Humusz → Növény    | tápanyag-kiegészítés a növekedéshez a fotoszintézis mellett    |
| Környezet → Növényevő/Ragadozó | metabolizmus-sebesség, mozgássebesség, halálozás    |
| Környezet → Lebontó | lebontási sebesség (pl. nedvesség, hőmérséklet-függés)         |
| Domborzat → Hőmérséklet | magasabb cellák hidegebbek ("lapse rate"), lásd 6.2         |
| Domborzat (mély terület) → Növény | a `water_tolerance` gén dönti el: alacsony        |
|                    | tolerancia esetén fokozatos elhervadás/pusztulás (`flood_stress`),|
|                    | magas tolerancia esetén korlátlan túlélés (vízinövény)         |
| Domborzat (mély terület) → Állat | lassítja/akadályozza a mozgást, de megbízható          |
|                    | vízforrás a szomjúság csillapítására                           |
| Azonos faj egyedei → egymás | szaporodás (ha közel vannak és mindkettőnek elég energiája van) |
| Sűrűség → mindegyik | túlnépesedés esetén erőforrás-verseny (implicit, a közös        |
|                    | táplálékkészleten keresztül, nem külön szabály)                |

### 4.7 Állapotok

Minden entitásnak van egy emberi olvasásra szánt **állapot-címkéje**
(`state`), amit minden `update()`-kor újraszámol a ténylegesen
végrehajtott viselkedés alapján – ez nem külön szimulációs mechanizmus,
hanem a már létező döntési logika (ki mit csinál éppen) láthatóvá tétele
a felhasználó számára, az entitás-inspectorban (lásd 8. fejezet) és a
térképen egy apró vizuális jelzéssel (pl. halványabb szín alváskor,
piros gyűrű menekülésnél, sárga gyűrű vadászatnál, szürke szín
halálkor).

| Állapot            | Mely fajoknál | Mikor aktív                                          |
|--------------------|---------------|-------------------------------------------------------|
| `Kóborol`          | mind a mozgó fajok | alapértelmezett, ha nincs sürgetőbb teendő        |
| `Éhes`             | Növényevő, Ragadozó, Lebontó | energiaszintje egy küszöb alá esik        |
| `Táplálékot keres` | Növényevő, Lebontó | talált táplálékforrás felé mozog                    |
| `Eszik`            | Növényevő, Ragadozó | táplálékot fogyaszt (harapás / sikeres vadászat)   |
| `Vadászik`         | Ragadozó      | zsákmányt üldöz vagy támad                            |
| `Bomlaszt`         | Lebontó       | detritust bont éppen humusszá                         |
| `Menekül`          | Növényevő     | ragadozó a látótávolságán belül                       |
| `Párosodik`        | Növényevő, Ragadozó, Lebontó | sikeres szaporodás pillanatában           |
| `Alszik`           | mind a mozgó fajok | éjszaka, ha nincs sürgető szükséglet (nem éhes,   |
|                    |               | nem menekül) – ilyenkor nem mozog, energiát spórol    |
| `Növekszik`        | Növény        | alapértelmezett, aktív fotoszintézis                  |
| `Hervad`           | Növény        | szélsőséges hőmérséklet, tartós vízhiány, vagy (ha    |
|                    |               | alacsony a `water_tolerance`) tartós elárasztás       |
| `Magot hint`       | Növény        | a szaporodás (magszórás) pillanatában                 |
| `Halott`           | mind          | lásd alább                                            |

**A "Halott" állapot**: amikor egy egyed elpusztul, a szimuláció nem
tünteti el azonnal – egy teljes tickig még a világban marad `Halott`
állapotban (kiválasztható, az inspectorban megfigyelhető), mielőtt
véglegesen eltávolítaná és a helyén detritust hagyna (lásd 4.5, 4.6).
Ez különösen hasznos, ha a felhasználó éppen szünet módban vagy
lépésenként (`step`) figyeli egy kiválasztott egyed sorsát: az elhalálozás
pillanata így nem villan el észrevétlenül.

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
    "decomposition_rate", "humus_yield",  # elsősorban a Decomposer-nél releváns
    "water_tolerance",  # elsősorban a Plant-nál releváns (lásd 4.2)
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
  `elevation` (domborzati magasság, lásd 6.2), `temperature`,
  `water_level`, `sunlight` (nappal/éjszaka + felhőzet alapján),
  `humus_level` (a lebontók által termelt tápanyag-szint). Az entitások
  folytonos (x, y) koordinátán mozognak, de a cella-értékeket a
  pozíciójuk alapján olvassák ki (bilineáris interpolációval a simább
  átmenetért).
- NumPy 2D tömbök a gyors frissítéshez; a hőmérséklet/víz terjedhet a
  szomszédos cellák között is (egyszerű diffúziós lépés minden tick-en),
  hogy ne legyenek éles, mesterséges határok.

### 6.2 Domborzat és állóvizek

- A rácshoz tartozik egy `elevation` mező is (relatív magasság, [0,1]-re
  normalizálva), amit induláskor egy zaj-alapú eljárás generál (pl.
  Perlin/simplex zaj, vagy egyszerűbben: néhány véletlen "hegycsúcs"
  körüli Gauss-görbe összegzése, majd enyhe simítás) – hasonló elven,
  mint a meglévő sziklaakadály-generátor, de folytonos magasságtérképet
  adva különálló akadálysziluettek helyett.
- A domborzatnak két hatása van:
  1. **Hőmérséklet-eltolás**: minél magasabban van egy cella, annál
     hidegebb, egyszerűsített "lapse rate" szerint, pl.
     `temperature -= elevation * TEMP_LAPSE_RATE`. Mivel a hőmérséklet
     mező már eddig is minden fajra hat (`temp_tolerance` sáv – lásd 4.1
     és a 4.6 Interakciós mátrix), a domborzat ezen a meglévő
     mechanizmuson keresztül közvetve befolyásolja a növényeket,
     növényevőket, ragadozókat és a lebontókat is.
  2. **Mély terület → állóvíz**: ha egy cella `elevation`-je egy
     beállítható `WATER_LEVEL` küszöb alatt van, a cella automatikusan
     "elárasztottnak" számít – állandóan magas `water_level` (pl. 1.0),
     ami szárazságban sem apad el. Ezek a cellák rajzolják ki a
     tavakat/tengert a térképen.
- Az állóvíz-cellák hatása a többi rendszerre:
  - **Növényekre**: állóvíz alatti cellába nem hajt gyökeret növény (a
    magszórás ezeket a sziklás cellákhoz hasonlóan kihagyja), viszont a
    közvetlen szomszédos szárazföldi cellákban a magas `water_level`
    miatt kedvezőbb a növekedés (nincs szárazság-stressz).
  - **Állatokra** (`Herbivore`/`Carnivore`/`Decomposer`): az állóvíz
    lassítja vagy akadályozza a mozgást (a meglévő terep-akadály
    mechanizmushoz hasonlóan, esetleg enyhébb "úszás-lassulás"
    formájában), de egyben megbízható, helyben elérhető vízforrást is
    jelent a szomjúság (`water_need`) csillapítására.
- A `WATER_LEVEL` küszöb és a `TEMP_LAPSE_RATE` a UI-ból is hangolható
  (lásd 6.4 Vezérlés), így a felhasználó szabályozhatja, mennyi
  hegyvidék/tenger legyen a térképen, és mennyire legyen zord a hegyvidéki
  klíma.
- A program **induláskor (és Resetkor) rögtön generál egy véletlen
  domborzatot**, amit a felhasználó a "Domborzat újragenerálása" gombbal
  bármikor, tetszőlegesen sokszor lecserélhet egy újabb véletlenre, amíg
  meg nem találja a neki tetsző térképet (lásd 6.5 Szerkesztő mód).

### 6.3 Paraméterek

| Paraméter        | Hatás                                                                 |
|-------------------|------------------------------------------------------------------------|
| **Hőmérséklet**   | Minden entitásnak van `temp_tolerance` sávja; ezen kívül energia-      |
|                   | vesztés/sebesség-csökkenés/halálozási esély nő. Növényeknél a          |
|                   | növekedési görbét módosítja. A domborzat ("lapse rate") és a nappal-   |
|                   | éjszaka/évszak ciklus együtt alakítja ki az alapértéket (lásd 6.2).    |
| **Domborzat**     | Magasságtérkép (`elevation`); hidegebbé teszi a magasan fekvő          |
|                   | cellákat, és a `WATER_LEVEL` küszöb alatti mély területeket állandó    |
|                   | állóvízzé (tó/tenger) alakítja (lásd 6.2).                             |
| **Víz**           | Cellánkénti víztartalom; növények növekedéséhez kell, növényevők/      |
|                   | ragadozók is elfogyaszthatják (csökkenti szomjúság-számlálójukat).     |
|                   | Az állóvíz-cellákban (lásd 6.2) állandóan magas, szárazságban sem      |
|                   | apadó vízforrást jelent.                                               |
| **Eső**           | Időszakos esemény, ami feltölti a víz-rácsot és hőmérsékletet enyhén  |
|                   | csökkenti; vezérelhető gyakoriság/intenzitás csúszkával.               |
| **Szárazság**     | Elhúzódó eső nélküli időszak: a víz-rács fokozatosan csökken,          |
|                   | fokozott stresszt okoz minden fajnak.                                  |
| **Humusz**        | Cellánkénti tápanyag-szint, amit a lebontók termelnek elhalt szerves   |
|                   | anyagból (`decomposition_rate` × `humus_yield` alapján, fajtánként     |
|                   | eltérő ütemben); a növények növekedési sebességét növeli a             |
|                   | fotoszintézis mellett. Utánpótlás híján lassan lebomlik/kimosódik.     |
| **Nappal/éjszaka**| Ciklikus fény-érték (szinusz görbe); befolyásolja a fotoszintézist,    |
|                   | egyes fajok éjszaka lassabbak/rejtettebbek (`camouflage` gén relevánsabbá|
|                   | válik éjszaka pl. ragadozóknál).                                       |

### 6.4 Vezérlés

- **Manuális mód**: csúszkák a UI-on (hőmérséklet alapszint, víz
  utánpótlás, eső valószínűség/erősség, nappal-éjszaka ciklus hossza és
  be/kikapcsolása, domborzat `WATER_LEVEL` küszöbe és `TEMP_LAPSE_RATE`
  hegyvidéki hőmérséklet-eltolás).
- **Automata mód**: beépített szezonális ciklus (pl. szinuszos évszak-
  szimuláció), amit a manuális csúszkák felülírhatnak.
- **Idő kontroll**: play/pause, sebesség-szorzó (0.5x–10x), "step"
  (egy tick léptetése pause alatt), reset gomb, ami visszaállítja a
  világot az üres szerkesztő módba (lásd 6.5).

### 6.5 Szerkesztő mód / kezdeti felállás

A program (és a "Reset" gomb) nem egy kész, véletlenszerűen benépesített
világgal indul, hanem egy **szerkesztő móddal**, ahol a felhasználó
állítja össze a kezdő helyzetet, mielőtt elindítaná az időt:

1. **Indulás kész domborzattal, üres populációval**: a program (és a
   "Reset" gomb) induláskor rögtön generál egy véletlen domborzatot
   (hegyekkel/tavakkal, lásd 6.2) – nem kell külön gombnyomás ahhoz, hogy
   legyen látható táj –, de egyetlen élőlény sincs még a világban. Amíg a
   felhasználó nem indítja el a szimulációt, az idő (és vele az időjárás,
   a növekedés, az öregedés stb.) nem telik – a világ "befagyasztva"
   várja a szerkesztést.
2. **Domborzat újragenerálása (opcionális)**: a "Domborzat
   újragenerálása" gomb tetszőlegesen sokszor lecseréli az aktuális
   magasságtérképet egy újabb véletlenre, amíg a felhasználó meg nem
   találja a neki megfelelő terepet.
3. **Egyedek elhelyezése**: a növények/növényevők/ragadozók/lebontók
   mindegyikéhez két lehetőség van egymás mellett:
   - **Kézi lehelyezés**: a "+ ... lehelyezése" gombbal aktivált módban a
     világra kattintva pontosan oda kerül egy új, véletlen genomú egyed
     (ismételt kattintással tetszőleges mintázat "kifesthető").
   - **Automatikus generálás**: egy "Automatikus generálás" gomb egy
     adott fajból egyszerre több egyedet szór szét véletlenszerűen a
     térképen – ez a gyors, "adj egy teljes kezdő populációt" jellegű
     opció, ami a manuális, egyenkénti lehelyezés alternatívája/
     kiegészítője. A darabszám **fajonként külön csúszkával
     beállítható** ("Kezdő növények/növényevők/ragadozók/lebontók: N db"),
     így a felhasználó szabja meg, mennyi egyeddel induljon (vagy
     egészüljön ki) az adott faj populációja – nincs rögzített
     alapértelmezett létszám. Növényeknél emellett egy "Kezdő víztűrő
     képesség" csúszka (lásd 4.2) is beállítja, hogy az induló
     (kézi/automatikus) növények `water_tolerance` génje milyen érték
     körül szóródjon – innentől a szárazságkedvelő/vízinövény irányú
     evolúciót a tényleges túlélés/szaporodás alakítja tovább.
   A domborzat-generáláshoz hasonlóan mindkét eszköz szerkesztés közben
   (a szimuláció elindítása előtt) a leghasznosabb, de attól még utólag,
   futás közben is használható marad.
4. **Nincs önmagától megjelenő egyed**: a populáció kizárólag az elhelyezett
   (kézi vagy automatikus) kezdő egyedekből és azok szaporodásából
   származhat – a szimuláció motorja sosem "varázsol elő" új egyedet
   spontán módon (pl. alacsony populáció esetén sem). Ha egy faj minden
   egyede elpusztul, az a faj véglegesen kihal, amíg a felhasználó a
   szerkesztő eszközökkel vissza nem tesz belőle; ez a valós kihalás
   lehetősége szándékos tervezési döntés, nem hiba.
5. **Szimuláció indítása**: a "Szimuláció indítása" gomb zárja le a
   szerkesztést és indítja el az időt – ettől kezdve a 7. fejezet szerinti
   update-ciklus fut tickenként, a szokásos pause/step/sebesség
   vezérlőkkel.

## 7. Szimulációs ciklus (fő update sorrend)

Az alábbi ciklus csak azután fut tickenként, hogy a felhasználó a
szerkesztő módban (lásd 6.5) megnyomta a "Szimuláció indítása" gombot –
addig a világ áll, a felhasználó szabadon szerkesztheti a domborzatot és
a kezdő populációt.

```
1. Idő előrehaladtatása (ha nincs pause), day/night fázis frissítése
2. Környezeti rács frissítése (eső esemény, diffúzió, szárazság csökkenés,
   humusz lassú lebomlása/kimosódása utánpótlás híján)
3. Térbeli particionálás frissítése (grid/quadtree a szomszéd-kereséshez)
4. Minden Plant.update()  → fotoszintézis + humusz-felvétel, növekedés,
   esetleges magszórás
5. Minden Herbivore.update() → érzékelés, mozgás, evés, menekülés, szaporodás
6. Minden Carnivore.update() → érzékelés, mozgás, vadászat, szaporodás
7. Minden Decomposer.update() → detritus lebontása, humusztermelés a
   helyi rácscellába (fajtánként eltérő `decomposition_rate`-tel)
8. Frissen elhunyt entitások "Halott" állapotba állítása és detritus
   létrehozása a helyükön (lásd 4.7); a *előző* tickben már megjelölt
   halottak tényleges eltávolítása; új entitások (utódok) hozzáadása
9. Statisztikák frissítése (populáció-számláló, átlagos gén-értékek)
10. Renderelés (világ + entitások + HUD + UI panel)
```

Nagy populációnál a 3. lépés (térbeli particionálás, pl. egyszerű
rács-alapú "spatial hashing") kritikus a teljesítményhez, hogy az
"legközelebbi étel/zsákmány/ragadozó" keresés ne legyen O(n²).

## 8. UI / Vezérlőpanel

- **HUD**: aktuális idő (nap/óra), populációszámok fajonként, FPS.
- **Szerkesztő/indítás eszközök** (lásd 6.5): "Domborzat újragenerálása"
  gomb, illetve egy "Szimuláció indítása" gomb, ami lezárja a szerkesztést
  és elindítja az időt. Amíg a szimuláció nincs elindítva, a felületen
  egy jól látható jelzés ("szerkesztő mód") emlékezteti a felhasználót.
- **Környezeti csúszkák**: hőmérséklet, víz utánpótlás, eső
  gyakoriság/erősség, nappal-éjszaka ciklus hossza, domborzat
  `WATER_LEVEL`/`TEMP_LAPSE_RATE` paraméterei, mutációs ráta.
- **Idő vezérlők**: pause/play, sebesség (1x/2x/5x/10x), step, reset (ami
  visszaállítja a világot az üres szerkesztő módba).
- **Entitás inspector**: kattintásra kiválasztott egyed adatai
  (aktuális **állapot** – lásd 4.7 –, tulajdonságok, energia, kor, DNS kód
  string, szülők generációja). Alapból a dekódolt (skálázott) tulajdonság-
  lista látszik a DNS-kód alatt; magára a **DNS-sorra kattintva** ez
  átvált egy részletes bontásra, ami soronként megmutatja, hogy a kód
  melyik pozíciója (karaktere) melyik génnek felel meg, mi a génhez
  tartozó nyers (0–1 közti) érték, és az milyen tényleges (skálázott)
  tulajdonság-értékké dekódolódik – így egy adott DNS-kód pontosan
  visszafejthető. Újbóli kattintással vissza lehet váltani a tömör
  nézetre.
- **Statisztika panel**: egyszerű vonaldiagram(ok) a populáció
  alakulásáról időben (Pygame-mel rajzolt polyline, nem kell külön lib).
- **Spawn eszköz**: minden fajhoz (növény/növényevő/ragadozó/lebontó)
  egy "Kezdő ... létszám" csúszka (0-tól a faj populáció-korlátjáig), és
  alatta egymás mellett két gomb – egy "+ ... lehelyezése" a kézi,
  kattintásos elhelyezéshez (adott pozícióba, véletlen genommal), és egy
  "Automatikus generálás" gomb, ami a csúszkával beállított darabszámú
  egyedet szór szét véletlenszerűen a térképen. A kettő tetszőlegesen
  kombinálható: pl. kézzel odarakott "mag"-populáció mellé automatikusan
  generált egyedek is kerülhetnek. Mivel (lásd 6.5, 4. pont) a szimuláció
  önmagától sosem hoz létre új egyedet, ez a két eszköz az egyetlen
  módja annak, hogy a kézzel/automatikusan elhelyezett és a szaporodásból
  származó egyedeken túl bármi más kerüljön a világba. Növényeknél egy
  külön "Kezdő víztűrő képesség" csúszka (lásd 4.2) állítja be az induló
  `water_tolerance` gén középértékét.

## 9. Fejlesztési fázisok (milestone-ok)

1. **Váz**: Pygame ablak, game loop, statikus rács megjelenítése,
   FPS-korlátozás.
2. **Környezet**: domborzat (`elevation`) generálása, hőmérséklet/víz
   rács (a domborzattól függő hőmérséklet-eltolással és a mély
   területeken keletkező állóvízzel), nappal-éjszaka ciklus, vizuális
   megjelenítés (pl. rács színezése hőtérképként), eső effekt.
3. **Növények**: `Plant` osztály, fotoszintézis-alapú növekedés,
   halál/szaporodás, alap genom nélkül (fix tulajdonságokkal).
4. **Genom rendszer**: `Genome` osztály bevezetése a növényekhez,
   mutáció + aszexuális öröklődés tesztelése (fenotípus-eltolódás
   megfigyelése generációkon át).
5. **Növényevők**: mozgás, érzékelés, táplálkozás, energia-menedzsment,
   ivaros szaporodás + crossover.
6. **Ragadozók**: vadászat, predáció, populáció-egyensúly tesztelése
   (klasszikus Lotka–Volterra-szerű oszcilláció megfigyelése).
7. **Lebontók és humusz-ciklus**: `Decomposer` osztály, detritus-objektumok
   elhalt entitásoknál, `humus_level` mező a környezeti rácsban, eltérő
   lebontási sebességű lebontó-variánsok, növények humusz-felvételének
   bekötése a növekedési függvénybe.
8. **UI vezérlők**: csúszkák a környezeti paraméterekhez, idő-vezérlés,
   spawn eszköz (kézi + automatikus generálás párban minden fajhoz),
   "Domborzat újragenerálása" és "Szimuláció indítása" gombok, illetve a
   szerkesztő mód (üres kezdő állapot, lásd 6.5) bekötése az egész
   szimuláció elé.
9. **Inspector + statisztikák**: kattintható entitás-részletező,
   populáció-grafikonok.
10. **Finomhangolás / egyensúlyozás**: alap paraméterek (metabolizmus,
   energiaértékek, mutációs ráta) hangolása, hogy a szimuláció hosszú
   távon se ne haljon ki azonnal, se ne robbanjon túlnépesedésbe.
11. **Polish / opcionális bővítések** (lásd 10. fejezet).

## 10. Lehetséges jövőbeli bővítések

- Fajok közötti hibridizáció-korlátozás (csak elég "hasonló" genomú
  egyedek szaporodhassanak egymással → fajképződés szimulálása).
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
  is kísérletezhessen vele. Mivel (lásd 6.5) nincs automatikus
  "bevándorlás" vagy önmagától megjelenő egyed, egy kihalt faj véglegesen
  eltűnik, amíg a felhasználó a szerkesztő eszközökkel vissza nem tesz
  belőle – ez szándékos, nem hiba, de a felhasználót érdemes erre
  felkészíteni (pl. a HUD-on jól látható populációszámokkal).
- **Determinizmus vs. változatosság**: érdemes egy globális seed opciót
  bevezetni a reprodukálható futtatásokhoz (debug/demo célra).
