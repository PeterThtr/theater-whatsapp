#!/usr/bin/env python3
"""Bedien-Ende für den Schub-Zug-Draht (Draht Ø 1,5 im PTFE-Schlauch 4/2): Gürtelhalter mit Schlauchklemme und Griff.

Halter (getragen senkrecht am Gürtel, Schlauch kommt von oben, Draht tritt unten aus, Griff hängt darunter):
  Koordinaten wie getragen: Y oben (am Körper entlang), X vom Körper weg, Z seitlich. Druckausrichtung: auf der Seite
  liegend, Z = Druckhöhe. Alles ist ein in Z extrudiertes Profil, daher ohne Stützen druckbar; die Biegung des Clips
  liegt in der Schichtebene (fest).
  - Clip: Zunge innen am Körper, Gurtspalt 4,5 mm, für Gürtel bis 40 mm Breite, unten mit Rastnase und Einführschräge.
  - Block außen: Bohrung Ø 4,0 für den Schlauch (Tropfenform, Spitze nach oben im Druck) von oben bis zur Schulter,
    darunter Ø 2,2 für den Draht mit trichterförmigem Austritt (der Draht knickt an der Kante nicht).
  - Klemme: Schlitz 1,0 von der Bohrung zur Oberseite (im Druck senkrecht), quer eine M3-Schraube (M3×10,
    Durchgang Ø 3,3, Kernloch Ø 2,6 zum Selbstschneiden). Leicht anziehen, sonst wird der Schlauch innen enger.
Griff: Flansch Ø 24 zum Ziehen (Finger dahinter), Schaft Ø 12, Kuppe zum Drücken mit dem Daumen.
  Draht in Bohrung Ø 1,6 (22 tief), geklemmt mit Gewindestift M3 (Kernloch Ø 2,6), dadurch die Drahtlänge einstellbar.
  Druck stehend, Flansch unten.

Aufruf: python3 bedienteil.py   -> out/*.stl, out/*.step
"""
import math, os
import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

W = 20.0                 # Breite (Z, Druckhöhe)
# Clip
T_ZUNGE, GURT = 2.6, 4.5
X_PLATTE0 = T_ZUNGE + GURT          # 7,1: Vorderplatte beginnt
T_PLATTE = 3.0
Y_CLIP_OBEN = 66.0
H_BRUECKE = 4.0
Y_ZUNGE_UNTEN = 8.0
# Block
X_B0 = X_PLATTE0 + T_PLATTE         # 10,1
X_B1 = X_B0 + 11.0                  # 21,1
Y_B1 = 80.0
XA, ZA = X_B0 + 4.4, 9.0            # Bohrungsachse (parallel Y)
D_SCHLAUCH, D_DRAHT = 4.0, 2.2
Y_SCHULTER = 14.0
SCHLITZ_B, Y_SCHLITZ = 1.0, (44.0, Y_B1)
Y_SCHRAUBE, Z_SCHRAUBE = 57.0, 15.6


def profil_halter():
    """Seitenprofil (X, Y) aus Clip, Vorderplatte und Block, mit Rundungen."""
    pts = [(0.0, Y_ZUNGE_UNTEN + 1.0), (1.0, Y_ZUNGE_UNTEN), (T_ZUNGE + 1.0, Y_ZUNGE_UNTEN),       # Zunge unten, Rastnase
           (T_ZUNGE + 1.0, Y_ZUNGE_UNTEN + 2.0), (T_ZUNGE, Y_ZUNGE_UNTEN + 4.0),
           (T_ZUNGE, Y_CLIP_OBEN - H_BRUECKE), (X_PLATTE0, Y_CLIP_OBEN - H_BRUECKE),                  # Gurtspalt oben
           (X_PLATTE0, 3.0), (X_PLATTE0 + 1.5, 0.0),                                                  # Vorderplatte unten mit Einführschräge
           (X_B1, 0.0), (X_B1, Y_B1), (X_B0, Y_B1), (X_B0, Y_CLIP_OBEN), (0.0, Y_CLIP_OBEN)]
    w = cq.Workplane("XY").polyline(pts).close().extrude(W)
    # senkrechte Kanten runden (im Druck senkrecht, kein Überhang)
    try:
        w = w.edges("|Z").fillet(0.8)
    except Exception:
        pass
    return w.val()


def bohrung_y(r, y0, y1):
    """Waagerechte Bohrung (im Druck) entlang Y mit Tropfenspitze nach +Z, Achse (XA, ZA)."""
    pts = [(0.0, r * math.sqrt(2))]
    for i in range(135, 405, 10):
        a = math.radians(i)
        pts.append((r * math.cos(a), r * math.sin(a)))
    pts.append((r * math.cos(math.radians(45)), r * math.sin(math.radians(45))))
    wp = cq.Workplane("XZ", origin=(XA, y0, ZA)).polyline(pts).close().extrude(-(y1 - y0))
    return wp.val()


def kegel_y(r0, r1, y0, y1):
    """Kegel entlang +Y um die Bohrungsachse (für Trichter)."""
    return cq.Solid.makeCone(r0, r1, y1 - y0, cq.Vector(XA, y0, ZA), cq.Vector(0, 1, 0))


def halter():
    s = profil_halter()
    s = s.cut(bohrung_y(D_SCHLAUCH / 2, Y_SCHULTER, Y_B1 + 1))
    s = s.cut(bohrung_y(D_DRAHT / 2, -1, Y_SCHULTER + 0.5))
    s = s.cut(kegel_y(2.6, D_DRAHT / 2, -0.01, 3.0))                 # Austrittstrichter Draht (Ø 5,2 -> 2,2)
    s = s.cut(kegel_y(D_SCHLAUCH / 2, 3.0, Y_B1 - 3.0, Y_B1 + 0.01))  # Einlauf Schlauch (Ø 4 -> 6)
    # Klemmschlitz: von der Bohrung bis zur Oberseite (Z = W), in der Ebene X = XA
    slot = cq.Workplane("XY").box(SCHLITZ_B, Y_SCHLITZ[1] - Y_SCHLITZ[0] + 1, W - ZA + 1, centered=False) \
        .translate((XA - SCHLITZ_B / 2, Y_SCHLITZ[0], ZA)).val()
    s = s.cut(slot)
    # Schraube M3 quer (entlang X) durch den Schlitz: Durchgang im äußeren Teil, Kernloch im inneren
    durch = cq.Solid.makeCylinder(1.65, X_B1 - XA + 1, cq.Vector(XA, Y_SCHRAUBE, Z_SCHRAUBE), cq.Vector(1, 0, 0))
    kern = cq.Solid.makeCylinder(1.3, XA - X_B0 + 0.01, cq.Vector(X_B0 + 0.0, Y_SCHRAUBE, Z_SCHRAUBE), cq.Vector(1, 0, 0))
    s = s.cut(durch).cut(kern)
    return s


# Griff
G_FLANSCH_R, G_FLANSCH_H = 12.0, 3.0
G_SCHAFT_R, G_SCHAFT_H = 6.0, 26.0
G_DRAHT_R, G_DRAHT_T = 0.8, 22.0
G_STIFT_Z = 12.0


def griff():
    p = [(0.0, 0.0), (G_FLANSCH_R - 0.5, 0.0), (G_FLANSCH_R, 0.5), (G_FLANSCH_R, G_FLANSCH_H - 0.8),
         (G_FLANSCH_R - 0.8, G_FLANSCH_H), (G_SCHAFT_R + 1.5, G_FLANSCH_H), (G_SCHAFT_R, G_FLANSCH_H + 1.5)]
    z0 = G_FLANSCH_H + G_SCHAFT_H
    p.append((G_SCHAFT_R, z0))
    for i in range(1, 25):
        a = math.radians(90 * i / 24)
        p.append((G_SCHAFT_R * math.cos(a), z0 + G_SCHAFT_R * math.sin(a)))
    p[-1] = (0.0, z0 + G_SCHAFT_R)
    s = cq.Workplane("XZ").polyline(p).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()
    loch = cq.Solid.makeCylinder(G_DRAHT_R, G_DRAHT_T + 0.01, cq.Vector(0, 0, -0.01), cq.Vector(0, 0, 1))
    trichter = cq.Solid.makeCone(1.6, G_DRAHT_R, 1.0, cq.Vector(0, 0, -0.01), cq.Vector(0, 0, 1))
    stift = cq.Solid.makeCylinder(1.3, G_SCHAFT_R + 0.1, cq.Vector(0, 0, G_STIFT_Z), cq.Vector(1, 0, 0))
    # Griffrillen im Schaft (flach, umlaufend) für besseren Halt
    s = s.cut(loch).cut(trichter).cut(stift)
    for k in range(4):
        z = G_FLANSCH_H + 8.0 + k * 4.0
        ring = cq.Workplane("XY").workplane(offset=z).circle(G_SCHAFT_R + 1).circle(G_SCHAFT_R - 0.4).extrude(1.2).val()
        s = s.cut(ring)
    return s


def export(s, name):
    bb = s.BoundingBox()
    s = s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, name + ".stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, name + ".step"))
    return s


if __name__ == "__main__":
    for name, s in (("bedien_halter_guertel", halter()), ("bedien_griff", griff())):
        assert s.isValid() and len(s.Solids()) == 1, name
        e = export(s, name)
        bb = e.BoundingBox()
        print(f"{name:24s} {s.Volume() / 1000 * 1.27:5.2f} g  {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm")
