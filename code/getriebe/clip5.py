#!/usr/bin/env python3
"""Winde mit Gürtelclip (Version 5): Gehäuseunterteil mit Sockel + angeschraubter Clip.

Getragen: Unterseite des Unterteils am Körper, Schlauchflansch (-x) zeigt nach oben, Drehrad (+y) seitlich
(von der Trägerin aus links). Der Sockel (4 mm, von unten ausgespart, Rand + Rippen + Schraubdome) schafft Platz
für zwei M3-Gewinde (Kernloch Ø 2,6, 5 tief, 1 mm unter dem Innenboden). Der Clip ist ein Profil
(Zunge, Gurtspalt 4,5, Platte 3), extrudiert in y (Breite 26) und liegend gedruckt (Biegung in der Schichtebene).
Befestigung: 2 × M3×8 Senkkopf (DIN 7991) von der Gurtseite durch die Platte; Kopf und Schraubendreher gehen
durch zwei Zugangslöcher Ø 6,8 in der Zunge. Gehäuse-Innenteile unverändert
(Rad, Schnecke, Welle, Drehrad, Deckel wie winde4).

Aufruf: NSTART=4 python3 clip5.py   -> out/winde5_gehaeuse_unterteil.*, out/winde5_guertelclip.*, out/winde5_ansicht.png
"""
import os
os.environ.setdefault("NSTART", "4")
import math
import cadquery as cq
import build4 as b4
from build3 import V, box, cylz, cylx, one, rot, on_bed, export, OX0, OX1, OY0, OY1, Z_BOT, Z_FLOOR, EARS, EAR_R

T_SOCKEL = 4.0
Z_S = Z_BOT - T_SOCKEL                 # neue Unterseite (-20,4)
SCREWS = [(4.0, 0.0), (19.0, 0.0)]     # (x, y) der Clipschrauben (im unteren Teil der Zunge, weg von der Biegung)
R_ZUGANG = 3.4                         # Zugangsloch Ø 6,8 in der Zunge für Kopf und Schraubendreher
R_KERN, T_KERN = 1.3, 5.0
RAND = 2.0

# Clip-Profil in (u, w): u = nach oben (= -x), w = vom Körper weg; w = W_PL1 liegt am Sockel an
T_ZUNGE, GURT, T_PL = 2.6, 4.5, 3.0
W_PL0 = T_ZUNGE + GURT                 # 7,1
W_PL1 = W_PL0 + T_PL                   # 10,1
U_TOP = -OX0                           # 15: Oberkante Clip = Oberkante Gehäuse (ohne Flansch)
H_BR = 4.0
U_GAP_TOP = U_TOP - H_BR               # 11: Gürteloberkante
U_ZUNGE_UNTEN = U_GAP_TOP - 44.0       # Gurtspalt 44 lang (Gürtel bis 40)
U_PL_UNTEN = U_ZUNGE_UNTEN - 3.0
B_CLIP = 26.0


def sockel_base():
    base = b4.build_base()
    bottom = base.faces("<Z")
    f = bottom if isinstance(bottom, cq.Face) else bottom
    faces = [fc for fc in base.Faces() if abs(fc.Center().z - Z_BOT) < 1e-6 and fc.normalAt().z < -0.99]
    sock = None
    for fc in faces:
        e = cq.Solid.extrudeLinear(fc, V(0, 0, -T_SOCKEL))
        sock = e if sock is None else sock.fuse(e)
    s = base.fuse(sock)
    # Taschen von unten (Gewicht): Rechteck innen, Rippen in x und y, Dome um die Schrauben
    pocket = box(OX0 + RAND, OX1 - RAND, OY0 + RAND, OY1 - RAND, Z_S - 1, Z_BOT)
    for xr in (4.5,):
        pocket = pocket.cut(box(xr - 0.8, xr + 0.8, OY0, OY1, Z_S - 2, Z_BOT + 1))
    pocket = pocket.cut(box(OX0, OX1, -0.8, 0.8, Z_S - 2, Z_BOT + 1))
    for x, y in SCREWS:
        pocket = pocket.cut(cylz(4.0, Z_S - 2, Z_BOT + 1, x, y))
    s = s.cut(pocket)
    for x, y in SCREWS:
        s = s.cut(cylz(R_KERN, Z_S - 0.1, Z_S + T_KERN, x, y))
        s = s.cut(cq.Solid.makeCone(R_KERN + 0.4, R_KERN, 0.4, V(x, y, Z_S - 0.01), V(0, 0, 1)))
    assert Z_S + T_KERN <= Z_FLOOR - 0.9
    return one(s.clean())


def clip_profil():
    p = [(U_ZUNGE_UNTEN + 1.0, 0.0), (U_ZUNGE_UNTEN, 1.0), (U_ZUNGE_UNTEN, T_ZUNGE + 1.0),        # Rastnase unten
         (U_ZUNGE_UNTEN + 2.0, T_ZUNGE + 1.0), (U_ZUNGE_UNTEN + 4.0, T_ZUNGE),
         (U_GAP_TOP, T_ZUNGE), (U_GAP_TOP, W_PL0),
         (U_PL_UNTEN + 3.0, W_PL0), (U_PL_UNTEN, W_PL0 + 1.5),                                  # Einführschräge
         (U_PL_UNTEN, W_PL1), (U_TOP, W_PL1), (U_TOP, 0.0)]
    return p


def clip():
    """Clip in Gehäusekoordinaten: x = -u, z = Z_S - (W_PL1 - w), Breite in y."""
    w = cq.Workplane("XY").polyline(clip_profil()).close().extrude(B_CLIP).val()   # (u, w, y')
    try:
        w = cq.Workplane().add(w).edges("|Z").fillet(0.8).val()
    except Exception:
        pass
    for x, y in SCREWS:
        u = -x
        hole = cq.Solid.makeCylinder(1.7, T_PL + 1, V(u, W_PL0 - 0.5, B_CLIP / 2 + y), V(0, 1, 0))
        cs = cq.Solid.makeCone(3.2, 1.7, 1.5, V(u, W_PL0 - 0.01, B_CLIP / 2 + y), V(0, 1, 0))
        cs2 = cq.Solid.makeCylinder(3.2, 1.0, V(u, W_PL0 - 1.0, B_CLIP / 2 + y), V(0, 1, 0))
        w = w.cut(hole).cut(cs).cut(cs2)
        w = w.cut(cq.Solid.makeCylinder(R_ZUGANG, T_ZUNGE + 2, V(u, -1.0, B_CLIP / 2 + y), V(0, 1, 0)))
    return one(w)


def clip_to_world(c):
    # (u, w, y') -> (x = -u, y = y' - B/2, z = Z_S - (W_PL1 - w))
    m = cq.Matrix([[-1, 0, 0, 0], [0, 0, 1, -B_CLIP / 2], [0, 1, 0, Z_S - W_PL1]])
    return c.transformGeometry(m)


if __name__ == "__main__":
    base = sockel_base(); c = clip()
    print("Unterteil", base.isValid(), round(base.Volume() / 1000 * 1.27, 1), "g;  Clip", c.isValid(), round(c.Volume() / 1000 * 1.27, 1), "g")
    cw = clip_to_world(c)
    print("Durchdringung Clip/Unterteil:", round(base.intersect(cw).Volume(), 3))
    hw = b4.handwheel_to_world(b4.build_handwheel())
    print("Durchdringung Clip/Drehrad:", round(hw.intersect(cw).Volume(), 3), " Abstand Drehrad-Unterkante zur Körperseite:",
          round(hw.BoundingBox().zmin - cw.BoundingBox().zmin, 1))
    export(on_bed(base), "winde5_gehaeuse_unterteil")
    export(on_bed(c), "winde5_guertelclip")                    # liegt mit der Profilfläche auf dem Bett (Breite = Druckhöhe)
    export(base, "winde5_gehaeuse_unterteil_montage", stl=False)
    export(cw, "winde5_guertelclip_montage", stl=False)
