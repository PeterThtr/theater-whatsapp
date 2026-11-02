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

---

## Teil C: TPU-Nasenprothese (Stand 1.11.2026, in Arbeit)

Code: `code/prothese/anprobe.py` (Scan-STL rein, Anprobe-Schale, mit `--fluegel` auch Flügel mit Bandschlitz) und `code/prothese/prothese.py` (komplette TPU-Prothese). Die Scandaten, Fotos und Maße liegen in `scan/` (siehe `scan/README.md`). Das Repo darf nicht öffentlich werden, die Daten zeigen Peters Gesicht.

- **Scan:** Scaniverse-STL (Meter, Mesh, 3164 Punkte, etwa 1 mm Kantenlänge). Der erste Scan (PLY) war ein Gaussian-Splat und wird nicht verwendet.
- **Maßstab geprüft:** Peter misst mit Messschieber Nasenlänge 51 mm (Nasenwurzel bis Spitze) und Nasenbreite 33,9 mm. Der Scan liefert etwa 52 mm (Nasenwurzel ist ein flacher Sattel, der Messpunkt schwankt um einige mm) und 31–33 mm. Maßstab 1,00 stimmt also. Eine frühere Messung mit 45,9 mm war ein Anzeigefehler des Messschiebers.
- **Entscheidungen von Peter:** Das Teleskop zeigt waagerecht vom Gesicht weg. Rund um die Nase soll eine breite Auflagefläche für Hautkleber sein.
- **Grenze des Scans:** Er reicht seitlich nur etwa 5–7 mm über die Nasenflügel hinaus und nach oben etwa 10 mm. Für eine breitere Auflage braucht es einen größeren Scanbereich (beide Wangen, Stirn bis Oberlippe).
- **Anprobe-Schale:** 0,8 mm Wand, zum Rand hin 0,4 mm auslaufend, 0,15 mm Spiel zur Haut, Nasenlöcher frei. Gedruckt wird sie stehend auf der unteren Kante mit Rand (Randtyp „Äußerer Rand“, 5–8 mm), praktisch ohne Stützen. **Gedruckt in PETG (1.11.): passt perfekt und liegt überall an, Maßstab 1,00 bestätigt. Ohne Kleber hält sie nur knapp und fällt bei Bewegung ab (starres PETG, noch kein Hautkleber getestet).**
- **TPU-Prothese V3 (2.11., gerechnet, nicht gedruckt) – aktuell:** Peter fand die V2 am Foto zu klobig: Flügel viel zu groß und auf den Augen, Nasenwurzel zu viel Material, Spitze nicht tief genug in der Prothese. Änderungen (`code/prothese/prothese.py`, `anprobe.py`): Maße des schlanken Drahtsatzes (`--draht`, aus `tele.py`): Hülse Außen-Ø 25,5 statt 32,4, Bohrung Ø 19,3, Fußtasche Ø 22,3. Gummiband **12 mm** (Peter, 2.11.), Schlitz 13 × 3,5. Flügel kleiner (Lappen 28–30 mm hoch, etwa 27 mm lang) und um 20° nach außen/unten geneigt, damit sie über den Wangenknochen und nicht auf den Augen liegen; Flügelachse an der Wurzel bei Y −10. Oberkante der Schale bei Y 14 statt 31. Die Unterseite der Spitze bleibt vor Z 15 erhalten, das TPU läuft also ein Stück unter die Nase (Nasenlöcher bleiben frei). Schlauchkanal weiter im Wulst am unteren Rand des Flügels bis zum Flügelende (Kanal-Ø 4,15, Länge etwa 88 mm). Fußplatte bei Z 41,5 (19 mm vor der Spitze), kleinster Biegeradius 13,6 mm (Grenze 13,0), Abstand Kanalmitte–Haut 4,5 mm, Wand zwischen Wulst und Schlitz 2,4 mm. Ergebnis: 100 × 45 × 125 mm (V2: 134 × 65 × 147), etwa 38 cm³, etwa 46 g bei 100 % (V2: 61 g). Aufruf: `python3 code/prothese/prothese.py scan/nase_scaniverse_original_m.stl --draht --austritt links --z-platte 32 --stutzen symmetrisch --winkel 25 --im-fluegel --out out/` (`--band 12` ist Standard). Aktuelle Datei `teile/aktuell/prothese/prothese_tpu.stl`, V2 in `teile/archiv/prothese/prothese_tpu_v2_fluegelkanal_dick.stl`. Die Abschnitte unten beschreiben V1/V2 (Feder-Maße), die Aufbauprinzipien gelten weiter.
  - **Druckergebnis V3 (2.11.):** Peter hat die V3 gedruckt (TPU, mit Stützen, die sich leicht entfernen ließen, und etwas Klebstoff auf der Druckplatte): **Druck klappte problemlos.** Der Rest (Passform am Gesicht, Schlauch, Band) ist noch nicht berichtet.
  - **Beidseitig und dünner (2.11.):** Auf Wunsch ist jetzt auch der rechte Tunnel gebohrt (`--stutzen beidseitig`): zwei spiegelgleiche Kanäle, der Schlauch kann links oder rechts laufen; der ungenutzte Kanal bleibt offen (mit Kleber oder einem Stück Schlauch verschließen). Der rechte Kanal hat mehr Wand zur Haut (6,6 mm gegenüber 4,5 mm links). Dateien in `teile/aktuell/prothese/`: `prothese_tpu_beidseitig.stl` (Wand 1,2, Flügel 2,0), `prothese_tpu_beidseitig_duenn.stl` (`--wand 0.8 --fluegel-dicke 1.5`, 35 cm³) und `prothese_tpu_beidseitig_duenn_achse-24.stl` (zusätzlich `--achse-y -24`, Teleskopachse 5 mm tiefer, 35 cm³, 50 mm hoch). Nur die druckfertige Lage (Hülse oben) liegt im Repo; die Lage wie im Scan entsteht mit dem Skript. Das Vorgängermodell (links offen, rechts Dummy) liegt in `teile/archiv/prothese/`.
  - **Holzstruktur (2.11.):** Peter möchte, dass die Prothese am Ende wie aus Holz geschnitzt aussieht. `--holz 1.0` (Standard 0 = aus) in `prothese.py` ruft `code/prothese/holz.py` auf. Die Außenfläche wird mit Manifold unterteilt (`refine_to_length`, größte Kante 0,9 mm, keine Risse) und entlang der Normalen verschoben: Jahresringe mit Stammachse parallel zur Nasenachse (Fladern), feine Längsfasern, vier Äste (konzentrische Ringe) und weiche Schnitzdellen, Tiefe etwa ±0,3 mm. Haut-Seite bleibt glatt (Gewicht über die Normale), alle Hohlräume werden danach exakt abgezogen, die Passmaße bleiben also unverändert. Datei `teile/aktuell/prothese/prothese_tpu_beidseitig_holz.stl` (Wand 1,0, Flügel 1,8, 36 cm³, 270 000 Flächen, 13,5 MB): `--wand 1.0 --fluegel-dicke 1.8 --holz 1.0 --stutzen beidseitig --austritt links --z-platte 32 --winkel 25 --im-fluegel --draht`. Dünnere Wand als 1,0 reicht mit dem Relief nicht (die Außenfläche geht bis 0,3 mm in die Wand). Das Relief ist 3 mm Ringabstand und ±0,3 mm, mit 0,4-mm-Düse und 0,12 Schicht druckbar. Der Holzeindruck kommt am Ende vor allem von der Bemalung (Grundton, Trockenpinsel für die Fasern, Lasur). Noch nicht gedruckt.
  - **Dicke gemessen (Mittelebene, mm von der Haut bis zur Außenfläche):** Nasenrücken Y +12/+8/+4: 0,4/1,2/1,1 (Wand 1,2) bzw. 0,2/0,9/0,7 (Wand 0,8); ab Y 0 wächst es durch den Keil vor der Nase auf 2,2 / 5,9 / 10,7 / 15,2 / 21,3 bei Y 0/−4/−8/−12/−16. Der Keil ist also die eigentliche Dicke, nicht die Schale. Achse −24 spart dort nur 1–3 mm. Mehr bringt nur ein kürzerer Weg von der Nasenspitze zur Fußplatte (Kanalkonzept) oder ein schlankerer Fuß/Hülse.
  - **Zum Gummiband:** 12 mm breit wurde von Peter gewählt. Der Druck unter dem Band hängt vom Zug ab (grob p = Zug / (Kopfradius 80 mm × Breite)): bei 2–4 N etwa 2–4 kPa, das ist bei einem weichen, flachen Band für ein paar Stunden aushaltbar, aber nicht erprobt. Zug begrenzen, Band nicht über die Ohren spannen.
- **TPU-Prothese V2 (1.11., gerechnet, nicht gedruckt):** `code/prothese/prothese.py` (baut auf `anprobe.py` auf), Ergebnis `teile/aktuell/prothese/prothese_tpu.stl` (druckfertige Lage, Hülse nach oben; aktuell links mit Kanal im Flügel, siehe unten) und `prothese_tpu_lage_scan.stl` (Lage wie im Scan). Aufruf: `python3 code/prothese/prothese.py scan/nase_scaniverse_original_m.stl --out out/ [--band 20] [--austritt unten|links|rechts] [--z-platte 38] [--kanal-radius 14] [--filet 5]`.
  - **Änderungen gegenüber V1:** Fußplatte 8 mm näher an der Nasenspitze (Z 38 statt 46, Abstand zur Spitze 15,5 mm), dafür Kanalbogen-Radius 14 statt 20 mm. Alle Übergänge sind mit 5 mm Radius verrundet (Voxel-Schließen, Hohlräume werden danach exakt abgezogen). Flügel sind runde Lappen (Wurzel 27 mm hoch, außen 42 mm, Gesamtbreite etwa 120 mm) mit Wölbung über dem Wangenknochen, der Rand läuft dünner aus. **V1 hatte einen Fehler:** Der Keil ragte etwa 4 mm in die Unterseite der Nasenspitze. Behoben, indem der Nasenkörper jetzt aus der vollständigen Scanfläche (mit Unterseite) abgezogen wird. V1-Dateien nicht verwenden.
  - **Aufbau (ein Körper, etwa 38 cm³, 119 × 65 × 143 mm):**
    - Schale auf der Haut: 1,2 mm Wand, zum Rand 0,5 mm, 0,15 mm Spiel zur Haut, Nasenlöcher frei.
    - Zwei Flügel, 2 mm dick (Rand dünner), Schlitz 21 × 3,5 mm für ein 20 mm breites flaches Gummiband in der Lappenmitte. Die Wangenform seitlich der Nase ist **geschätzt** (Steigung −0,4, Radius 75, Wölbung in Y Radius 90), der Scan reicht dort nicht.
    - Keil (konvexe Hülle) von der Nasenspitze zur Hülse, Hülse Außen-Ø 32,4 mit 45 mm Länge um Segment 1, davon 18,5 mm frei.
    - Teleskopachse waagerecht auf Höhe der Nasenspitze (Y −19). Fußplatte-Rückseite bei Z 38.
    - Bohrung für Segment 1 Ø 27,1 (0,5 mm Übermaß = Presssitz, TPU dehnt sich). Fußtasche Ø 30,2 für den runden Fuß (Ø 29,8, Platte + Becher), eine Schulter hält ihn in beide Richtungen.
    - Kanal Ø 3,9 für den 4-mm-PTFE-Schlauch, Biegeradius 14 mm, Austritt unten vorn bei Y −29, Z 25 (Richtung nach unten), 5 mm von der Haut entfernt.
  - **Seitlicher Kanal im Flügel, Peter nimmt links (1.11.):** Der Schlauch soll möglichst spät zu sehen sein und dann hinter dem Ohr nach unten zum Gürtel laufen. Der Kanal (Ø 4,15 zum Einschieben des 4-mm-Schlauchs, Länge etwa 116 mm) läuft in der Achsebene (Y −19) als S-Kurve (zwei Bögen mit R 14, erster Bogen 58°) um die Nasenspitze, dann spitz (25°) nach hinten zur Wange, folgt dann in einem Wulst (Außen-Ø 8,2) der Außenfläche des Flügels unter dem Schlitz hindurch bis zum äußeren Flügelrand und tritt dort bei X −61, Y −7, Z −44 nach hinten/oben aus (kurzer Stutzen mit gerundeter Kante). Der Flügelumriss wächst unter dem Wulst mit (Rippe am unteren Rand). Der Schlitz für das Band sitzt dafür 4 mm höher als die Flügelmitte, Abstand Kanalmitte–Schlitz 7,2 mm. Aufruf: `--austritt links --z-platte 36 --stutzen symmetrisch --winkel 25 --im-fluegel`; `prothese.py` schiebt die Fußplatte selbst so weit vor, wie Wand (mindestens 4 mm Abstand Kanalmitte–Haut) und Biegeradius (mindestens 13,2) es verlangen: Z 41,5, also 19 mm vor der Spitze (vorher 15 mm). Das ist der Preis für den langen Kanal. Kleinster Radius 13,9 mm.
  - **Wulst und Gegenstück (1.11.):** Alle Übergänge sind mit 5 mm Radius verrundet. **Auf der anderen Seite sitzt ein spiegelgleicher Wulst mit Stutzen ohne Bohrung** (Symmetrie, nur Optik); er kann bei Bedarf als zweiter Schlauchweg gebohrt werden. `--stutzen aus|einseitig|symmetrisch`. Die Schale selbst folgt der echten Nase und ist nur so symmetrisch wie die Nase. Aktuelle Datei: `teile/aktuell/prothese/prothese_tpu.stl` (etwa 134 × 65 × 147 mm, etwa 51 cm³, etwa 61 g bei 100 %). Ältere Varianten (unten, rechts, quer, Stutzen spitz ohne Flügelkanal) liegen in `teile/archiv/prothese/`.
  - **Geprüft am Modell:** wasserdicht, ein Körper, auch nach einem STL-Hin-und-Rück-Lauf; der Spalt zur Haut ist frei und die Wand geschlossen; kein TPU in Nase, Tasche, Bohrung und Kanal.
  - **Nicht geprüft / offen:** nie gedruckt. Ob der 4/2-mm-PTFE-Schlauch den Bogen mit 14 mm Radius ohne Knick schafft (Test: um ein Rohr mit Ø 28 mm legen); sonst `--z-platte 46 --kanal-radius 20`. Der Fuß muss von vorn durch die Bohrung (Dehnung etwa 10 %), mit Seifenwasser. Segment 1 hat noch **keine Haltenuten**, es hält über den Presssitz. Für die Schnur-Variante mit 2-mm-Schlauch ist der Kanal zu weit. Die Flügelform ist geraten. Gewicht hoch (etwa 40–46 g bei 100 %, die meiste Masse ist Wand und Keil).
  - **Druck:** Lage Hülse nach oben, Höhe 143 mm, Überhang (Neigung < 30°) etwa 4 cm². Die Flügel stehen nur mit ihren Kanten auf der Platte (Rand „Äußerer Rand“ nötig). Ob Stützen nötig sind, zeigt die Vorschau in Bambu Studio.
- **Offen:** Anprobe mit Flügeln und Band (PETG) wäre sinnvoll, bevor in TPU gedruckt wird. Haltenuten und Segment-1-Anpassung, Antrieb und Anbindung des Drahts (Teil D).

## Teil D: Drahtvariante statt Feder (Stand 2.11.2026, Elemente neu gerechnet, nichts gedruckt)

- **Idee:** Ein starrer Federstahldraht in einem PTFE-Schlauch schiebt und zieht die Nase (Schub-Zug-Kabel). Die Feder entfällt. Das Einziehen läuft wie bisher über Kappe und Ringe.
- **Schlauch:** PTFE 4/2 mm (3D-Drucker-Bowdenschlauch). Draht: Federstahl 1,5 mm (1,8 mm ist zu steif und schwer zu bekommen). Das Spiel von 0,25 mm je Seite ergibt grob 2 mm Totgang bei 270° Gesamtkrümmung. Ein dünnerer Schlauch mit gleichem Innen-Ø bringt nichts.
- **Knicklast** (Euler, beidseitig gelenkig, 245 mm frei): 1,5 mm etwa 9 N, 1,0 mm etwa 1,8 N, 2,0 mm etwa 28 N. Litzenseil trägt weit weniger und kommt zum Schieben nicht infrage.
- **Test 1 (Peter, 1.11.):** Der Draht lässt sich gut durch den Schlauch schieben. Senkrecht auf die Küchenwaage gedrückt: 0,3 kg, dann biegt sich der Schlauch, maximal 0,4 kg (etwa 3–4 N). Das misst den frei verbogenen Schlauch, nicht den freien Draht. Offen: Test 2 mit eingespanntem Schlauch (3–5 cm) und 245 mm freiem Draht. Erwartung etwa 0,9 kg.
- **Offen:** Reibung des gedruckten Teleskops messen (wie viel Schub braucht das Ausfahren?). Antrieb mit 186 mm Hub, der schieben und ziehen kann (die Winde zieht nur). Anbindung des Drahts an die Kappe (Sackloch von unten, Klemmschraube oder Epoxid). Fuß mit Aufnahme für den 4-mm-Schlauch. Ohne Feder könnten die Segmente schlanker werden (Parameter `RI5` in `tele.py`).

- **Elemente für den Draht (2.11., gerechnet, nicht gedruckt):** `TELE_PROFIL=draht python3 code/nase/export_all.py` (und `verify.py`, `render.py`) erzeugt den schlanken Satz mit Dateien `nase_draht_*` und `probe_draht_*`, abgelegt in `teile/aktuell/nase_draht/` (STL und STEP, dazu `nase_draht_schnitt.png`). Ohne die Variable bleibt alles wie bei der Feder (Regression geprüft: Volumina identisch). Der Parameter `RI5` (Bohrung Segment 5) legt alle Radien fest.
  - **Maße:** Außen-Ø Segment 1–5: 19,8 / 15,8 / 12,2 / 8,6 / **5,0** mm (vorher 27,6 / 23,6 / 20,0 / 16,4 / 12,8). Bund-Ø 17,1 / 13,5 / 9,9 / 6,3. Bohrung Segment 5 Ø 3,4 (Draht 1,5), Wand Segment 5 0,8, Segmente 2–4 1,0, Segment 1 1,2. Längen, Spiel (0,15), Ringspalt (0,8), Hub (185,8 mm) und alle Anschläge unverändert. Eingefahren 69,5 mm, ausgefahren 255,3 mm. Masse etwa 18,6 g statt 32,7 g bei 100 %.
  - **Kappe:** Sackloch Ø 1,7 von unten für den Draht (11 mm tief, mit 2K-Epoxid oder Sekundenkleber einkleben), Schaft Ø 3,2, Kappen-Ø 6,4. **Fuß rund:** Becher Ø 21,9, Plattenloch Ø 1,8, kurze Drahtführung (R 2,5, 1,4 hoch, bleibt unter Segment 5). Der Flügelfuß hat weiter seine Flügel (±24), aber noch keine Schlauchaufnahme (die übernimmt die TPU-Prothese).
  - **Geprüft am Modell:** keine Durchdringungen in beiden Endlagen, Anschläge wie vorher; laut `bs_support_sim.py` keine Stützen (Segmente mit Opferfuß). **Offen:** Segment 5 steht nur auf einem Bund-Ø 6,3, also Opferfuß und Rand nötig. Der Draht läuft frei durch Bohrungen von Ø 3,4 bis 17,4, geführt wird er nur in Segment 5. Die Prothese (Hülse, Fußtasche) ist noch auf die alten Maße gerechnet und muss angepasst werden.

## Nächste Schritte (Peters Rückmeldung abwarten)

1. Passprobe Teleskop: Sitz des Spiels 0,15. Bei Bedarf `S` in `tele.py` ändern, neu exportieren und `verify.py` laufen lassen.
2. Teleskop V2 komplett drucken und montieren: Durchhang, Stick-Slip, Federführung.
3. Winde mit den winde4-Teilen: Lagersitz, Halt der eingeklebten Welle, Bremse.
4. TPU-Prothese V3 drucken oder vorher die Anprobe mit Flügeln in PETG testen (siehe Teil C). Dazu die schlanken Teleskopelemente (Teil D) drucken.
