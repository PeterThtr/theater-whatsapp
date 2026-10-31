import os
"""Winde komplett: Gehäuse (Unterteil + Deckel), Schnecke mit Wellenzapfen, Kurbel.

Koordinaten wie in der geprüften Baugruppe:
  Rad/Trommel-Achse = Z durch (0,0), Radmitte z = 0 (Trommelunterseite z = -13.8, Radoberseite z = +3.0)
  Schneckenachse parallel Y durch (13.5, 0, 0), Schnecke um y = 0 zentriert.
Trennebene des Gehäuses: z = 0 (geht durch die Schneckenachse -> geteilte Lager).
"""
import math, os, sys
import numpy as np
import cadquery as cq
import env, worm2

V = cq.Vector
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
A = env.A  # 13.5

# ---------------------------------------------------------------- Maße
Z_BOT = -16.4           # Unterseite Unterteil
Z_FLOOR = -14.4         # Innenboden
Z_BOSS = -13.9          # Anlaufring der Trommel (Trommelunterseite liegt bei -13.8)
Z_CEIL = 8.0            # Decke innen (Schneckenkopf 7.5)
Z_TOP = 10.0            # Oberseite Deckel
CAV_X0, CAV_X1 = -12.8, 21.8
CAV_Y0, CAV_Y1 = -13.7, 13.7
WALL_X, WALL_Y = 2.6, 3.0
OX0, OX1 = CAV_X0 - WALL_X, CAV_X1 + WALL_X      # -15.0 .. 24.0
OY0, OY1 = CAV_Y0 - WALL_Y, CAV_Y1 + WALL_Y      # -16.7 .. 16.7
EAR_R = 3.7
EARS = [(OX0 - 0.9, OY0 - 0.9), (OX0 - 0.9, OY1 + 0.9), (OX1 + 0.9, OY0 - 0.9), (OX1 + 0.9, OY1 + 0.9)]
BEAR_R_NEG, BEAR_R_POS = 2.7, 3.2   # Lagerbohrung -y (Welle O5) / +y (Welle O6)
BEAR_R = 2.2            # Lagerbohrung Ø4.4 für Wellenzapfen Ø4.0
PIN_D = 3.0
CORD_Y, CORD_Z = -10.25, -11.15      # Schnur tritt tangential am Kern (r=10) aus, auf Nutmitte
TUBE_HOLE_R = 1.15      # PTFE-Schlauch AD 2 mm


def box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cylz(r, z0, z1, x=0.0, y=0.0):
    return cq.Solid.makeCylinder(r, z1 - z0, V(x, y, z0), V(0, 0, 1))


def cyly(r, y0, y1, x=0.0, z=0.0):
    return cq.Solid.makeCylinder(r, y1 - y0, V(x, y0, z), V(0, 1, 0))


def cylx(r, x0, x1, y=0.0, z=0.0):
    return cq.Solid.makeCylinder(r, x1 - x0, V(x0, y, z), V(1, 0, 0))


def one(shape):
    sol = shape.Solids()
    assert len(sol) == 1, f"{len(sol)} Körper"
    return sol[0]


# ---------------------------------------------------------------- Unterteil
def build_base():
    s = box(OX0, OX1, OY0, OY1, Z_BOT, 0.0)
    for ex, ey in EARS:
        s = s.fuse(cylz(EAR_R, Z_BOT, 0.0, ex, ey))
    # Feder (Nut-Feder-Verbindung zum Deckel)
    ring = box(CAV_X0 - 1.8, CAV_X1 + 1.8, CAV_Y0 - 1.8, CAV_Y1 + 1.8, 0.0, 1.0).cut(
        box(CAV_X0 - 0.8, CAV_X1 + 0.8, CAV_Y0 - 0.8, CAV_Y1 + 0.8, -0.1, 1.1))
    s = s.fuse(ring)
    s = s.cut(box(CAV_X0, CAV_X1, CAV_Y0, CAV_Y1, Z_FLOOR, 0.5))
    # Anlaufring + Stiftloch (Stahlstift Ø3)
    s = s.fuse(cylz(4.0, Z_FLOOR - 0.1, Z_BOSS))
    s = s.cut(cylz(PIN_D / 2 + 0.05, -15.9, Z_BOSS + 0.1))
    # PTFE-Schlauch: Block außen am -x-Ende, Bohrung, Trichter innen
    s = s.fuse(box(OX0 - 6.0, OX0 + 0.1, CORD_Y - 3.5, CORD_Y + 3.5, Z_BOT, CORD_Z + 3.5))
    s = s.cut(cylx(TUBE_HOLE_R, OX0 - 7.0, CAV_X0 + 0.5, CORD_Y, CORD_Z))
    s = s.cut(cq.Solid.makeCone(TUBE_HOLE_R, 2.6, 2.0, V(CAV_X0 - 1.9, CORD_Y, CORD_Z), V(1, 0, 0)))
    # halbe Lagerbohrungen für die Schnecke
    s = s.cut(cyly(BEAR_R, OY0 - 1, OY1 + 1, A, 0.0))
    # Schraubenlöcher M3 (selbstschneidend)
    for ex, ey in EARS:
        s = s.cut(cylz(1.35, -12.0, 0.1, ex, ey))
    return one(s.clean())


# ---------------------------------------------------------------- Deckel
def build_cover():
    s = box(OX0, OX1, OY0, OY1, 0.0, Z_TOP)
    for ex, ey in EARS:
        s = s.fuse(cylz(EAR_R, 0.0, Z_TOP, ex, ey))
    s = s.cut(box(CAV_X0, CAV_X1, CAV_Y0, CAV_Y1, -0.1, Z_CEIL))
    groove = box(CAV_X0 - 1.9, CAV_X1 + 1.9, CAV_Y0 - 1.9, CAV_Y1 + 1.9, -0.1, 1.2).cut(
        box(CAV_X0 - 0.7, CAV_X1 + 0.7, CAV_Y0 - 0.7, CAV_Y1 + 0.7, -0.2, 1.3))
    s = s.cut(groove)
    s = s.fuse(cylz(4.0, 3.3, Z_CEIL + 0.1))
    s = s.cut(cylz(1.65, 3.2, 9.0))
    s = s.cut(cyly(BEAR_R_NEG, OY0 - 1, 0.0, A, 0.0)).cut(cyly(BEAR_R_POS, 0.0, OY1 + 1, A, 0.0))   # Lager: -y O5.4 / +y O6.4
    for ex, ey in EARS:
        s = s.cut(cylz(1.7, -0.1, Z_TOP + 0.1, ex, ey))
        s = s.cut(cylz(3.2, Z_TOP - 3.2, Z_TOP + 0.1, ex, ey))
    return one(s.clean())


# ---------------------------------------------------------------- Schnecke (lokal: Achse Z, um 0 zentriert)
SHAFT_END = 26.7
FLAT_X = 1.6
FLAT_Z0 = 16.9


def build_worm():
    th = worm2.make_worm(length=24.0, bore=None).val()
    s = th
    for z0, z1 in ((-13.5, -11.5), (11.5, 13.5)):
        s = s.fuse(cylz(4.0, z0, z1))
    s = s.fuse(cylz(2.0, -16.5, -13.4)).fuse(cylz(2.0, 13.4, SHAFT_END))
    s = s.cut(box(FLAT_X, 3.0, -3.0, 3.0, FLAT_Z0, SHAFT_END + 1))
    return th, one(s.clean())


# ---------------------------------------------------------------- Kurbel (lokal: Achse Z, Arm +X, Druck: +Y oben)
HUB_L = 8.0
PLATE_T = 4.0
ARM_R = 15.0
HUB_R = 5.0
KNOB_R = 5.0
KNOB_L = 12.0
HUB_Y0 = 17.2           # Weltposition y der Nabenunterkante
GRUB_Y = 22.7           # Weltposition y der Madenschraube
BED_CUT = -4.2          # Auflagefläche (Abflachung) in lokal y


def build_crank():
    hub = cylz(HUB_R, 0.0, HUB_L)
    plate = (cq.Workplane("XY").workplane(offset=HUB_L - 0.01).center(ARM_R / 2, 0)
             .slot2D(ARM_R + 2 * HUB_R, 2 * HUB_R, 0).extrude(PLATE_T + 0.01)).val()
    knob = cylz(KNOB_R, HUB_L + PLATE_T - 0.01, HUB_L + PLATE_T + KNOB_L, ARM_R, 0.0)
    s = hub.fuse(plate).fuse(knob)
    # D-Bohrung: Ø4.2 mit Fläche bei +Y (Abstand 1.7)
    dh = cylz(2.1, -0.1, 9.9).intersect(box(-3, 3, -3, 1.7, -0.2, 10.0))
    s = s.cut(dh)
    # Madenschraube (M3 selbstschneidend) auf die Wellenfläche, Richtung +Y
    s = s.cut(cq.Solid.makeCylinder(1.3, 8.0, V(0, 0.8, GRUB_Y - HUB_Y0), V(0, 1, 0)))
    # Auflagefläche
    s = s.cut(box(-20, 40, -10, BED_CUT, -1, 40))
    return one(s)          # kein clean(): erzeugt hier einen ungültigen Körper


# ---------------------------------------------------------------- Transformationen
def rot(shape, axis, deg):
    ax = {"x": V(1, 0, 0), "y": V(0, 1, 0), "z": V(0, 0, 1)}[axis]
    return shape.rotate(V(0, 0, 0), ax, deg)


def worm_to_world(s):
    return rot(s, "x", -90).translate(V(A, 0, 0))


def crank_to_world(s):
    s = rot(s, "z", -90)            # D-Fläche (+Y lokal) -> +X wie bei der Welle
    s = rot(s, "x", -90)            # Achse Z -> Y
    return s.translate(V(A, HUB_Y0, 0))


def on_bed(s):
    bb = s.BoundingBox()
    return s.translate(V(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def export(solid, name, stl=True, step=True):
    wp = cq.Workplane(obj=solid)
    if step:
        cq.exporters.export(wp, f"{OUT}/{name}.step")
    if stl:
        cq.exporters.export(wp, f"{OUT}/{name}.stl", tolerance=0.005, angularTolerance=0.06)


if __name__ == "__main__":
    import time
    t0 = time.time()
    base = build_base(); print("Unterteil", base.isValid(), round(base.Volume(), 1), round(time.time() - t0, 1), flush=True)
    cover = build_cover(); print("Deckel   ", cover.isValid(), round(cover.Volume(), 1), flush=True)
    th, worm = build_worm()
    exp = th.Volume() + 2 * math.pi * 16 * 1.5 + math.pi * 4 * (3.1 + (SHAFT_END - 13.4)) \
        - math.pi * 4 * 0.0
    print("Schnecke ", worm.isValid(), round(worm.Volume(), 1), " Gewindekörper", round(th.Volume(), 1), flush=True)
    crank = build_crank(); print("Kurbel   ", crank.isValid(), round(crank.Volume(), 1), flush=True)

    # --- Weltlage (Zusammenbau) -> STEP
    worm_w = worm_to_world(worm)
    crank_w = crank_to_world(crank)
    export(base, "winde_gehaeuse_unterteil_montage", stl=False)
    export(cover, "winde_gehaeuse_deckel_montage", stl=False)
    export(worm_w, "winde_schnecke_montage", stl=False)
    export(crank_w, "winde_kurbel_montage", stl=False)

    # --- Druckausrichtung -> STL + STEP
    export(on_bed(base), "winde_gehaeuse_unterteil")
    export(on_bed(rot(cover, "x", 180)), "winde_gehaeuse_deckel")
    export(on_bed(rot(rot(worm, "y", -90), "x", 0)), "winde_schnecke_mit_welle")
    export(on_bed(rot(rot(crank, "x", 90), "x", 0).translate(V(0, 0, 0))), "winde_kurbel")
    for f in sorted(os.listdir(OUT)):
        if f.startswith("winde_"):
            print(f, os.path.getsize(f"{OUT}/{f}") // 1024, "kB")
    print("gesamt", round(time.time() - t0, 1), "s")
