# Nasenscan von Peter (für die Pinocchio-Nase und andere Projekte)

**Steckbrief zum Kopieren in andere Chats:**
Nase von Peter, 3D-Scan mit Scaniverse (iPhone), Mesh in Millimetern, Maßstab geprüft (Messschieber: Nasenlänge 51 mm, Nasenbreite 33,9 mm; gedruckte PETG-Anprobe passt perfekt). Koordinaten: X seitlich, Y oben, Z aus dem Gesicht heraus, Ursprung in der Mitte des zugeschnittenen Scans. Nasenspitze bei etwa X 0, Y −19, Z +22 mm. Nasenrücken von der Nasenwurzel zur Spitze etwa 46–52 mm (flacher Sattel, Messpunkt schwankt), Nasenflügelbreite etwa 31–33 mm im Scan.

| Datei | Inhalt |
|---|---|
| `nase_scaniverse_original_m.stl` | Originaldatei aus Scaniverse, Einheit Meter, so wie exportiert |
| `nase_scan_mm_zentriert.stl` | dasselbe in mm, in die Mitte verschoben (mit dieser Datei arbeitet `code/prothese/anprobe.py` intern) |
| `nase_mittelschnitt_profil.csv` | Profil der Mittelebene (Y oben, Z nach vorn) |
| `nase_masse.json` | Messwerte (Peter und aus dem Scan) mit Hinweisen |
| `fotos/` | Fotos von unten, von der Seite und von vorne (ohne Maßstab) |
| `archiv/` | erster Scan als Gaussian-Splat (PLY), unbenutzt, nur zur Sicherheit |

## Eigenschaften des Scans
- Mesh mit etwa 3200 Punkten und 1 mm Kantenlänge, keine fehlerhaften Dreiecke, offen nur am Zuschnittrand.
- Zugeschnitten: seitlich nur 5–7 mm über die Nasenflügel hinaus, oben etwa 10 mm über die Nasenwurzel, unten bis zum Nasenfuß. Für breitere Auflagen oder Brillen/Masken braucht man einen größeren Scan.
- Nasenlöcher und Spitzenunterseite sind sichtbar, aber nicht präzise.

## Verwendung (Python)
```python
import trimesh
m = trimesh.load("scan/nase_scan_mm_zentriert.stl")   # mm
```
Die Originaldatei in Metern wird mit `m.apply_scale(1000)` nach mm umgerechnet; für den Zentrierten Stand danach `m.apply_translation(-m.bounds.mean(0))`.

Dies sind Daten über eine reale Person (Peters Gesicht). Das Repo nicht öffentlich machen.
