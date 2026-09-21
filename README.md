# Élet Szimuláció

Pygame alapú 2D élet-szimuláció: növények, növényevők, ragadozók és lassan
mozgó lebontó szervezetek élnek, táplálkoznak, szaporodnak és halnak meg
egy szabályozható környezetben (domborzat, hőmérséklet, víz, eső,
nappal/éjszaka). A térkép domborzata (magasságtérkép) hidegebbé teszi a
hegyvidéki cellákat, a mély területeken pedig állandó állóvíz (tó/tenger)
alakul ki, ami elzárja az utat a mozgó élőlények elől, de a szomszédos
szárazföldet is öntözi. Az elpusztult egyedekből "detritus" keletkezik,
amit a lebontók humusszá alakítanak – ez a humusz gyorsítja a növények
növekedését. Minden entitásnak van egy DNS-szerű genetikai kódja, ami
szaporodáskor (crossover + mutáció) öröklődik és formálja az utódok
tulajdonságait.

A program **szerkesztő módban indul**: induláskor rögtön generál egy
véletlen domborzatot (hegyekkel/tavakkal), de élőlény még nincs a
világban, és az idő sem telik, amíg a felhasználó össze nem állítja a
kezdő helyzetet (a domborzat újra is generálható, majd növények és
állatok helyezhetők el kézzel vagy automatikus generálással), és meg nem
nyomja a "Szimuláció indítása" gombot.

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

- **"Domborzat újragenerálása" gomb** – új véletlen magasságtérképet
  (hegyek/tavak) generál; szerkesztés közben tetszőlegesen sokszor
  megnyomható, amíg a felhasználó meg nem találja a neki tetsző térképet
- **"+ ... lehelyezése" gombok** – kattintással pontosan odahelyez egy
  új növényt/növényevőt/ragadozót/lebontót a világ tetszőleges pontjára
  (ESC törli a folyamatban lévő lehelyezést)
- **"Auto +N" gombok** – az adott fajból egyszerre N véletlenszerűen
  elszórt egyedet helyez el (a kézi lehelyezés gyors alternatívája)
- **"Szimuláció indítása" gomb** – lezárja a szerkesztést és elindítja az
  időt; előtte a világ "befagyasztva" áll, hogy nyugodtan össze lehessen
  állítani a kezdő helyzetet
- **SPACE** – szünet / folytatás (a szimuláció elindítása után)
- **S** – egy lépés léptetése (szünet alatt hasznos)
- **R** – újraindítás: új véletlen domborzattal és üres populációval
  visszaállítja a szerkesztő módot
- **Bal kattintás a világon** – kiválasztott entitás adatainak (DNS-kód,
  tulajdonságok, energia) megjelenítése a jobb oldali panelen
- **Kattintás a DNS sorra** (kiválasztott egyednél) – megmutatja a DNS-kód
  részletes bontását: melyik karakter melyik gént kódolja, mi a nyers és
  a tényleges (skálázott) értéke; újbóli kattintással visszavált a tömör
  tulajdonság-listára
- **Jobb oldali csúszkák** – időskálázás, alap hőmérséklet, eső esélye
  és intenzitása, a tó/tenger szintje (domborzati küszöb), a hegyvidék
  hidegebb volta, mutációs ráta és erősség élőben állítható
- **"Eső: Automata / Kényszerítve BE / KI" gomb** – manuálisan
  felülbírálható az automata időjárás

## Felépítés

```
config.py            - alapértelmezett paraméterek, gén-tartományok
entities/
  genome.py           - DNS-szerű genom: crossover, mutáció, dekódolás
  base.py, mobile.py   - közös entitás-logika
  plant.py             - fotoszintézis (humusszal is), magszórás
  herbivore.py          - táplálkozás, menekülés, szaporodás
  carnivore.py          - vadászat, szaporodás
  decomposer.py         - lassú mozgás, detritus lebontása humusszá
world/
  environment.py       - domborzat, hőmérséklet/víz/humusz rács (NumPy), diffúzió
  detritus.py           - elhullott entitásokból keletkező szerves törmelék
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

Egyedek kizárólag szaporodással jöhetnek létre – nincs automatikus
"bevándorlás" vagy önmagától megjelenő egyed –, így egy faj tartósan ki is
halhat, ha egy rossz ciklusban minden egyede elpusztul; ekkor a
felhasználó a szerkesztő eszközökkel (kézi lehelyezés vagy automatikus
generálás) tud újra egyedeket helyezni a világba.
