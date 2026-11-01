# Pinocchio-Nase – Übergabe (Stand 31.10.2026)

Dieses Verzeichnis enthält den kompletten Stand eines Projekts aus einer früheren Claude-Sitzung:
Code (CadQuery-Generatoren, Prüfskripte), aktuelle Druckdateien und diese Zusammenfassung.

## Zusammenarbeit mit Peter

- Peter ist Theatertechniker (Ausbildung Elektronik) und arbeitet mit Fusion 360, einem **Bambu Lab A1 und A1 Mini** (je nach Verfügbarkeit; 0,4-mm-Düse, Textured PEI Plate), PETG und TPU.
- **Antworten auf Deutsch.** Begriffe aus Bambu Studio und Fusion 360 müssen die **echten deutschen Menübezeichnungen** sein, nicht selbst übersetzte. Bambu-Studio-Begriffe wurden aus `bbl/i18n/de/BambuStudio_de.po` im Repo `bambulab/BambuStudio` geprüft (siehe `code/bs/po.py`, der Pfad zur .po-Datei steht oben im Skript und muss angepasst werden).
- Er druckt selbst und meldet Ergebnisse zurück. Alle Konstruktionen sind **gerechnet und am Modell geprüft, aber erst teilweise gedruckt**. Das bei Empfehlungen offen sagen.
- Er will druckfertige STL-Dateien (richtig ausgerichtet, möglichst ohne Stützen) und STEP-Dateien für Fusion.

## Das Projekt

Ausfahrbare Nase für die Pinocchio-Rolle (Bühnenrequisit, wird der Schauspielerin ins Gesicht geklebt, also leicht halten):

- Ein Teleskop aus 5 PETG-Segmenten. Eine Edelstahl-Druckfeder drückt es auseinander: Draht 0,8 mm, Außen-Ø 10 mm, frei 305 mm, Rate etwa 0,081 N/mm, etwa 57 Windungen, Blocklänge geschätzt 46 mm.
- Eine Angelschnur durch die Federmitte zieht es ein.
- Die Schnur läuft in einem PTFE-Schlauch (Außen-Ø 2 mm) zu einer **Winde an der Gürtelschnalle**. Die Schauspielerin fährt die Nase damit selbst in Etappen aus.
- Später soll Segment 1 in eine **TPU-Nasenprothese** übergehen (Scan der Nase per App). Der Fuß bekommt dafür seitliche Flügel mit Löchern, die das TPU formschlüssig umschließt, weil PETG und TPU schlecht aneinander haften.

---

## Teil A: Teleskop V2 (neu konstruiert am 31.10., noch nicht gedruckt)

Code: `code/nase/tele.py` (Parameter und Geometrie), `export_all.py` (STL/STEP), `verify.py` (Kollisionen und Anschläge in beiden Endlagen), `render.py` (Schnittbilder).
Dateien: `teile/aktuell/nase/`.

Die alten Segmentmaße (Basis-Ø 26,6, Segmentlänge 58, etwa 10 mm Überlappung) standen nicht mehr zur Verfügung. Deshalb wurde komplett neu konstruiert. Die neuen Teile passen nicht zu den alten.

**Maße** (z = Achse, z = 0 = Oberseite Fußplatte):

| Teil | Bohrung Ø | außen Ø | Bund Ø (unten) | Lippe Ø (oben innen) | Länge |
|---|---|---|---|---|---|
| Segment 1 | 25,2 | 27,6 (Wand 1,2) | – | 23,9 | 63,5 |
| Segment 2 | 21,6 | 23,6 | 24,9 | 20,3 | 62 |
| Segment 3 | 18,0 | 20,0 | 21,3 | 16,7 | 62 |
| Segment 4 | 14,4 | 16,4 | 17,7 | 13,1 | 62 |
| Segment 5 | 10,8 (Feder) | 12,8 | 14,1 | – (Kappe) | 62 |

- **Spalt und Spiel:** Ringspalt G = 0,8. Radiales Spiel S = 0,15 an Lippe und Bund. Bund und Lippe ragen je 0,65 über.
- **Bund:** 10 mm hoch, mit 45°-Kegel oben.
- **Lippe:** 5 mm Führung mit 45°-Kegel unten. Beim Ausfahren liegt Kegel auf Kegel und zentriert sich selbst.
- **Führung:** 15,5 mm Überlappung je Fuge, ausgefahren.
- **Ringe 2–4:** flach, 1,2 mm dick, Bohrung = Lippe + 0,2. Sie werden oben auf Segment 2–4 geklebt. Unten außen haben sie eine 45°-Fase (0,7), oben innen eine Senkung (0,7). Beim Einziehen nimmt jedes innere Segment über seinen Ring das nächstäußere mit. Ohne diese Ringe würde nur Segment 5 einfahren. Die Ringe werden nur auf Druck belastet. Ring 2 sitzt in der eingebauten Senkung oben in Segment 1.
- **Kappe:** Halbkugel R 7,1 mit Schacht Ø 10,6 in Segment 5. Der Übergang ist ein 45°-Kegel, dazu die Senkung in Segment 5. Ein 0,4 mm breiter Absatz bleibt, PETG druckt ihn ohne Stützen. Das Knotenfenster ist ein Quer-Tropfenloch Ø 3,5, darunter ein Mittelloch Ø 1,2. Die Feder drückt auf die Schachtunterseite.
- **Fuß** (eigenes Teil, nötig, weil die Segmente von unten eingeschoben werden): Platte 1,5 mm, Becher für Segment 1 (innen +0,05, außen Ø 29,8, 4 hoch), Federdorn R 4 × 2, Schnurloch Ø 1,5 mit Einläufen. Die Flügel reichen bis x = ±24, sind 11 breit und haben je 2 Löcher Ø 3 bei x = 17,6 und 21. `nase_fuss_rund.stl` ist die Variante ohne Flügel.
- **Ergebnis der Prüfung:**
  - Länge eingefahren 73,4 mm, ausgefahren 259,2 mm, Schnurweg 185,8 mm (Winde bleibt unverändert).
  - Federlänge 55,8 mm eingefahren (etwa 20 N), 241,6 mm ausgefahren (etwa 5 N).
  - Masse etwa 33 g bei 100 % Füllung.
  - Keine Durchdringungen. Anschläge liegen an (Abstand 0 bzw. 0,035 mm Klebe-/Luftspalt).
  - Laut `bs_support_sim.py` keine Stützen nötig.
- **Durchhang:** Durch das Spiel kann die Spitze rechnerisch bis etwa 9 mm durchhängen, wenn die Nase waagrecht steht.
- **Druck:**
  - Segmente stehend mit dem Bund unten, Ringe flach, Kappe mit dem Schacht unten, Fuß mit der Platte unten.
  - 0,12 mm, Stützen aus.
  - Elefantenfußkompensation etwa 0,15 mm.
  - Nahtposition „Ausgerichtet“, Schrägnaht-Typ „Kontur und Bohrung“.
  - Passung über X-Y-Konturkompensation und X-Y-Loch-Kompensation (Qualität → Präzision) nachjustieren.
  - Zuerst die Passprobe drucken: `probe_segment3_kurz.stl` und `probe_segment4_kurz.stl` (24 mm lang).
- **Opferfuß (1.11., noch nicht gedruckt):** `segment(k, opfer=True)` erzeugt `nase_segment{1..5}_opferfuss` und `probe_segment{3,4}_kurz_opferfuss` (STL und STEP).
  - Aufbau: Die Außenfase unten am Bund ist 0,6 statt 0,3. Eine Scheibe 0,8 dick reicht bis Bund-R + 7. Sie ist nur über einen Steg 0,35 dick und 1 mm breit angebunden, der in die Fase hineinläuft (`opferfuss_schnitt.png`).
  - Nach dem Druck den Steg bündig an der Bund-Gleitfläche abschneiden. Der Rest liegt innerhalb der Fase.
  - Geprüft im ungünstigsten Fall (Rest füllt die Fase ganz): keine Durchdringungen; laut `bs_support_sim.py` keine Stützen nötig.
  - Randtyp dazu „Keine Umrandung“, die Scheibe ersetzt den Rand.
  - Die Teile ohne Opferfuß sind unverändert (Außenfase 0,3).
- **Montagereihenfolge:**
  1. Segment 2 von unten in Segment 1 schieben, Ring 2 kleben.
  2. Segment 3 von unten durch alles schieben, Ring 3 kleben. Segment 4 und Ring 4 genauso.
  3. Segment 5 von unten einschieben. Die Schnur an der Kappe knoten, von oben durch Segment 5 fädeln, Kappe kleben.
  4. Die Feder von unten über die Schnur schieben, Schnur durch den Fuß führen.
  5. Den Fuß kleben. Dabei die Schnur unter dem Fuß festhalten.
- **Gleiten:** Ein hauchdünner Film Silikonfett oder PTFE-Spray auf den Gleitflächen hilft gegen Stick-Slip. Die Gleitflächen nicht lackieren.
- **Offene Ideen:**
  - Dünne TPU- oder Filzringe als Dämpfung an den Anschlägen (Klacken auf der Bühne).
  - Kopfringe zum Einrasten statt Kleben.
  - Eine PTFE-Schlauchaufnahme am Fuß hängt von der TPU-Prothese ab.

---

## Teil B: Winde an der Gürtelschnalle (Schneckengetriebe)

Code: `code/getriebe/`. Generator ist `build4.py` (nutzt `build3.py`, `worm3.py`, `env.py`). Aktueller Stand: `MODE=welle6 NSTART=4 python3 build4.py`. Prüfung: `NSTART=4 python3 verify6.py` (etwa 2,5 min; liest `out/schneckenrad_mit_trommel_4gang.step`).

**Getriebe:**
- Modul 1,5, Schneckenrad z = 10 (Teilkreis-R 7,5, Kopf-R 9), viergängige Schnecke (Teil-Ø 12, Kopf-R 7,5, Fuß-R 4,2, Steigung 18,85 mm, Steigungswinkel 26,6°).
- Achsabstand 13,5, Flankenspiel etwa 0,16.
- Trommelkern Ø 20, etwa 25 mm Schnur pro Drehradumdrehung, 7,4 Umdrehungen für 185 mm.
- **Nicht selbsthemmend.** Gehalten wird über eine Reibbremse: M3-Gewindestift mit Filz auf den Bremsbund R 7,2.
- Die Axialkraft der Schnecke (etwa 27 N) drückt immer Richtung −y gegen den unteren Bund.

**Gehäuse:**
- Unterteil und Deckel, Trennebene in der Schneckenachse, 4 × M3.
- Stahlstift Ø 3 × 24 als Radachse.
- PTFE-Schlauch-Flansch mit 4 mm Knickschutz.
- Drehrad Ø 46 mit Fingerlöchern statt Kurbel.

**Verlauf:**
- V1: Kurbel, eingängig. Zu langsam und hakelig.
- V2: viergängig. Läuft deutlich leichter.
- Die stehend gedruckte, einteilige Schnecke brach nach wenigen Umdrehungen am Ø4-Wellenstück am Eintritt ins Drehrad. Vermutete Ursache: Die Schichten lagen quer zur Welle.
- Lösung: eine **getrennte PETG-Welle, liegend gedruckt** (flache Seite unten, Wandlinien 6, 100 %, 0,12). Sie wird mit 2K-Epoxid in einen **Schneckenkörper mit großer Bohrung** geklebt (Ø 5,5, D-Fläche).
- Keine Stahlwelle, weil sie nicht schnell beschaffbar war. Nicht aufreiben: D-Bohrungen nur mit Schleifpapier am Stab nacharbeiten.

**Aktueller Teilesatz** (`teile/aktuell/winde/`):
- `winde2_rad_mit_trommel.stl`: gedruckt, passt.
- `winde3_drehrad.stl`: gedruckt, passt. Nabe R 6, Bohrung Ø 6,1 mit D-Fläche bei 1,7. **Nicht neu drucken.**
- `winde4_welle.stl`: Zapfen −y Ø 5 (auch im Schneckenkörper), ab der Schulter bei y = 13,6 Ø 6 (Lager +y und Drehradsitz).
- `winde4_schnecke_koerper.stl`: stehend, ohne Stützen.
- `winde4_gehaeuse_unterteil.stl` und `winde4_gehaeuse_deckel.stl`: Lagerbohrungen Ø 5,4 / Ø 6,4.
- **Stand:** Die winde4-Teile sind ausgeliefert, aber noch nicht gedruckt. Peters Rückmeldung zur Passung steht aus.
- **Prüfung am Modell:**
  - Alle Durchdringungen 0.
  - Rad–Schnecke 0,167, Schnecke–Gehäuse 0,196, Drehrad–Schnecke 0,147.
- **Beim Einkleben** der Welle liegt sie im Unterteil, mit Backpapier dazwischen.

Überholt (Archiv in `teile/archiv/winde/`): `winde_*`, `winde2_*` (außer dem Rad), `winde3_*` (außer dem Drehrad).

**Erwogen, aber zurückgestellt:**
- Motorantrieb mit N20-Getriebemotor, 6 V, 150 U/min.
- Reine Schraubenbremse ohne Kurbel.

---

## Werkzeuge und Fallstricke

- **Umgebung:** Python 3 mit `cadquery` (2.8), `trimesh`, `shapely`, `scipy`, `vtk`, `matplotlib`. Installation mit `pip install cadquery trimesh shapely scipy vtk matplotlib` (pip ggf. mit `--break-system-packages`).
- **`code/bs/bs_support_sim.py <stl> 0.12`:** Nachbau der Überhangerkennung „Normal (auto)“ von Bambu Studio (Schwelle 30°). Die STL muss in Druckausrichtung vorliegen.
- **CadQuery:**
  - Zwei Teile mit Spalt per `fuse` vereinigen ergibt zwei Körper. Dafür `cq.Compound.makeCompound` verwenden.
  - `clean()` kann Körper ungültig machen. Danach immer `isValid()` prüfen.
- **trimesh:** Schnitte mit `section_multiplane` machen, nicht `to_2D()` pro Schnitt, sonst verschieben sich die Bezugssysteme.
- **Prozesse:** Nie `pkill -f`/`pgrep -f` mit einem Muster verwenden, das in der eigenen Kommandozeile steht. Das beendet die eigene Shell. Stattdessen `ps aux | grep "[v]erify"` und dann per PID beenden.
- **Bambu-Studio-Begriffe (geprüft, deutsch):**
  - Schichthöhe; Stützstrukturen aktivieren; Typ: Normal (auto) / Baum (auto); Schwellenwinkel; Nur auf Druckplatte.
  - Qualität → Naht: Nahtposition (Ausgerichtet / Rückseite / Zufällig / Nächste), Schrägnaht-Typ (Keine / Kontur / Kontur und Bohrung).
  - Qualität → Präzision: Präzise Wand, Elefantenfußkompensation, X-Y-Loch-Kompensation, X-Y-Konturkompensation.
  - Qualität → Erweitert: Reihenfolge der Wände (innen/außen, außen/innen).
  - Stärke → Wände → Wandlinien; Fülldichte.
  - Sonstige → Druckbetthaftung → Randtyp.
  - Profile „0.12mm Fine @BBL A1“ / „@BBL A1M“ (A1 Mini) und „Generic PETG @BBL A1“ / „@BBL A1M“. Haftung: Segmente stehen nur auf einem schmalen Ring. Auf dem A1 Mini lösen sich PETG-Teile trotz großem äußeren Rand nach wenigen Schichten, auf dem A1 deutlich seltener. Z-Hop beim Rückzug war schon 0,4 mm, Profil „@BBL A1M“ war richtig gewählt. Befund: Der Rand bleibt liegen, das Teil reißt vom Rand ab (Lücke stand auf 0,1, Elefantenfußkompensation war schon 0). Segment 2 einzeln, 50 %, mit Rand: nach etwa 2/3 der Höhe von der Platte gerutscht (1.11.). Ursache laut Modell: Die Segmente stehen wegen Innenfase 0,6 und Außenfase 0,3 nur auf einem 0,75 mm breiten Ring. Deshalb gibt es jetzt den Opferfuß (siehe Teil A).

## Nächste Schritte (Peters Rückmeldung abwarten)

1. Passprobe Teleskop: Sitz des Spiels 0,15. Bei Bedarf `S` in `tele.py` ändern, neu exportieren und `verify.py` laufen lassen.
2. Teleskop V2 komplett drucken und montieren: Durchhang, Stick-Slip, Federführung.
3. Winde mit den winde4-Teilen: Lagersitz, Halt der eingeklebten Welle, Bremse.
4. TPU-Prothese nach Scan; der Fuß mit den Flügeln ist vorbereitet.
