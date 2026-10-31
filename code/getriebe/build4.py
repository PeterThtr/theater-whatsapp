"""Winde Version 2: 4-gängige Schnecke, Drehrad mit Fingerlöchern, Schlauchflansch mit Tülle, Reibbremse.

Wird mit NSTART=4 ausgeführt (Gangzahl der Schnecke / des Rades).
Koordinaten wie build3: Radachse = Z durch (0,0), Schneckenachse parallel Y durch (13.5, 0, 0).
"""
import os
os.environ.setdefault("NSTART", "4")
import math, sys
import numpy as np
import cadquery as cq
import env, worm3
import build3 as b3
from build3 import (BEAR_R_NEG, BEAR_R_POS, V, box, cylz, cyly, cylx, one, rot, on_bed, export, A, Z_BOT, Z_FLOOR, Z_BOSS, OX0, OX1, OY0, OY1,
                    CAV_X0, CAV_X1, CAV_Y0, CAV_Y1, EAR_R, EARS, BEAR_R, PIN_D, CORD_Y, CORD_Z, OUT)

NS = env.NS
WTAG = f"_{NS}gang"

# ---------------------------------------------------------------- Schlauchflansch + Tülle (Knickschutz)
TUBE_R = 1.1            # Bohrung Ø2.2 für PTFE-Schlauch AD 2 (Druck macht Löcher meist etwas kleiner)
CORD_HOLE_R = 0.7       # Schnurloch Ø1.4 in der Schulter
X_STOP = CAV_X0 - 1.0   # Schulter: Schlauchende stößt hier an (-13.8)
FLANGE_L = 6.0          # Länge des Flanschblocks
NOZ_L = 4.0             # Länge der konischen Tülle (Knickschutz)
NOZ_R0, NOZ_R1 = 3.5, 1.9
KEEL_T = 2.2            # Stützsteg unter der Tülle (druckbar ohne Stützmaterial)

# ---------------------------------------------------------------- Bremssäule
PIL_X = 4.0             # halbe Breite
PIL_Y1 = 23.0
PIL_TOP = -7.8
BRAKE_Y = 19.6          # Mitte des Bremsbundes (Welt-y)


def build_base():
    s = box(OX0, OX1, OY0, OY1, Z_BOT, 0.0)
    for ex, ey in EARS:
        s = s.fuse(cylz(EAR_R, Z_BOT, 0.0, ex, ey))
    ring = box(CAV_X0 - 1.8, CAV_X1 + 1.8, CAV_Y0 - 1.8, CAV_Y1 + 1.8, 0.0, 1.0).cut(
        box(CAV_X0 - 0.8, CAV_X1 + 0.8, CAV_Y0 - 0.8, CAV_Y1 + 0.8, -0.1, 1.1))
    s = s.fuse(ring)
    s = s.cut(box(CAV_X0, CAV_X1, CAV_Y0, CAV_Y1, Z_FLOOR, 0.5))
    s = s.fuse(cylz(4.0, Z_FLOOR - 0.1, Z_BOSS))
    s = s.cut(cylz(PIN_D / 2 + 0.05, -15.9, Z_BOSS + 0.1))
    # Flanschblock (wie bisher) + konische Tülle + Stützsteg
    s = s.fuse(box(OX0 - FLANGE_L, OX0 + 0.1, CORD_Y - 3.5, CORD_Y + 3.5, Z_BOT, CORD_Z + 3.5))
    noz = cq.Solid.makeCone(NOZ_R0, NOZ_R1, NOZ_L, V(OX0 - FLANGE_L + 0.1, CORD_Y, CORD_Z), V(-1, 0, 0))
    s = s.fuse(noz)
    # Stützsteg: Halbbreite 0.707*R(x) -> Überhang der Tülle überall höchstens 45°
    xb = OX0 - FLANGE_L + 0.2
    h = CORD_Z - Z_BOT
    w0 = 2 * 0.707 * (NOZ_R0 - 0.1)
    w1 = 2 * 0.707 * (NOZ_R1 + 0.05)
    keel = (cq.Workplane("YZ", origin=(xb, 0, 0)).center(CORD_Y, Z_BOT + h / 2).rect(w0, h)
            .workplane(offset=-(NOZ_L - 0.4)).rect(w1, h).loft(combine=True)).val()
    s = s.fuse(keel)
    # Bohrung: Schlauchsitz bis zur Schulter, dahinter Schnurloch + Trichter zur Trommel
    x_tip = OX0 - FLANGE_L - NOZ_L
    s = s.cut(cylx(TUBE_R, x_tip - 1.0, X_STOP, CORD_Y, CORD_Z))
    s = s.cut(cylx(CORD_HOLE_R, X_STOP - 0.5, CAV_X0 + 0.5, CORD_Y, CORD_Z))
    s = s.cut(cq.Solid.makeCone(CORD_HOLE_R, 1.8, CAV_X0 - X_STOP, V(X_STOP, CORD_Y, CORD_Z), V(1, 0, 0)))
    # Bremssäule unter dem Bremsbund des Drehrads, Gewinde M3 von unten
    s = s.fuse(box(A - PIL_X, A + PIL_X, OY1 - 0.1, PIL_Y1, Z_BOT, PIL_TOP))
    s = s.cut(cylz(1.3, Z_BOT - 1, PIL_TOP + 1.0, A, BRAKE_Y))
    s = s.cut(cyly(BEAR_R_NEG, OY0 - 1, 0.0, A, 0.0)).cut(cyly(BEAR_R_POS, 0.0, OY1 + 1, A, 0.0))
    for ex, ey in EARS:
        s = s.cut(cylz(1.35, -12.0, 0.1, ex, ey))
    return one(s.clean())


def build_cover():
    return b3.build_cover()


# ---------------------------------------------------------------- Schnecke (4 Gänge) mit Welle
SHAFT_END = 29.5
FLAT_X = 1.6
FLAT_Z0 = 16.9


def build_worm(chamfer=True, thrust_chamfer=True):
    th = worm3.make_worm(length=24.0, bore=None).val()
    if chamfer:
        # 45°-Fase am unteren Gewindeende (z=-12): Stirnseite wird druckbar ohne Stützen (stehend, Zapfen unten).
        # Liegt ausserhalb des Eingriffs (Rad greift nur bei |z| < 6.7).
        ring = cylz(9.0, -12.1, -8.6).cut(cq.Solid.makeCone(4.1, 7.6, 3.5, V(0, 0, -12.1), V(0, 0, 1)))
        th = th.cut(ring)
    s = th
    for z0, z1 in ((-13.5, -11.5), (11.5, 13.5)):
        s = s.fuse(cylz(4.0, z0, z1))
    s = s.fuse(cylz(2.0, -16.5, -13.4)).fuse(cylz(2.0, 13.4, SHAFT_END))
    if thrust_chamfer:
        # Axialfase unter dem unteren Bund (stehender Druck, Zapfen unten): Der Schnurzug schiebt die Schnecke IMMER nach -y,
        # also gegen diesen Bund. 45°-Kegel von R=4.0 (z=-12.3) bis R=2.8 (z=-13.5); es bleibt ein ebener Anlaufring R 2.0..2.8.
        keep = cq.Solid.makeCone(2.7, 4.1, 1.4, V(0, 0, -13.6), V(0, 0, 1))
        s = s.cut(cylz(5.0, -13.6, -12.2).cut(keep))
    # Wellenfläche auf lokal -Y  ->  Welt +Z (Madenschraube von oben erreichbar)
    s = s.cut(box(-3.0, 3.0, -3.0, -FLAT_X, FLAT_Z0, SHAFT_END + 1))
    return th, one(s.clean())


# ---------------------------------------------------------------- Drehrad (lokal: Achse Z, Welle-Fläche +Y)
HUB_Y0 = 17.2            # Weltposition y der Nabenunterkante
HUB_R = 6.0
HUB_LEN = 13.8
BUND_R = 7.2
BUND_L = 4.4
CONE_L = BUND_R - HUB_R
DISC_R = 23.0
DISC_Z0 = 8.2
N_HOLES = 5
HOLE_D = 11.5
HOLE_RC = 14.8
GRUB_Z = 6.6
BORE_END = 12.7          # Welle endet bei 29.5 -> lokal 12.3


def build_handwheel():
    hub = cylz(HUB_R, 0.0, HUB_LEN)
    bund = cylz(BUND_R, 0.0, BUND_L)
    cone = cq.Solid.makeCone(BUND_R, HUB_R, CONE_L, V(0, 0, BUND_L), V(0, 0, 1))
    disc = cylz(DISC_R, DISC_Z0, HUB_LEN)
    s = hub.fuse(bund).fuse(cone).fuse(disc)
    for k in range(N_HOLES):
        a = math.radians(90.0 + 360.0 * k / N_HOLES)
        s = s.cut(cylz(HOLE_D / 2, DISC_Z0 - 1, HUB_LEN + 1, HOLE_RC * math.cos(a), HOLE_RC * math.sin(a)))
    for k in range(36):                      # Griffkerben am Rand
        a = math.radians(10.0 * k)
        s = s.cut(cylz(1.0, DISC_Z0 - 1, HUB_LEN + 1, (DISC_R + 0.4) * math.cos(a), (DISC_R + 0.4) * math.sin(a)))
    dh = cylz(3.15, -0.1, BORE_END).intersect(box(-4, 4, -4, 1.85, -0.2, BORE_END + 0.1))
    s = s.cut(dh)
    s = s.cut(cq.Solid.makeCylinder(1.3, 7.0, V(0, 0.8, GRUB_Z), V(0, 1, 0)))
    return one(s)


def worm_to_world(s):
    return b3.worm_to_world(s)


def handwheel_to_world(s):
    s = rot(s, "z", 180)             # Wellenfläche +Y lokal -> -Y
    s = rot(s, "x", -90)             # Achse Z -> Y, -Y -> +Z
    return s.translate(V(A, HUB_Y0, 0))


# ---------------------------------------------------------------- gestufte PETG-Welle (liegend gedruckt) + Schneckenkoerper mit D-Bohrung
FLAT_D = 1.6


def build_worm_koerper():
    th = worm3.make_worm(length=24.0, bore=None).val()
    ring = cylz(9.0, -12.1, -8.6).cut(cq.Solid.makeCone(4.1, 7.6, 3.5, V(0, 0, -12.1), V(0, 0, 1)))
    s = th.cut(ring)
    for z0, z1 in ((-13.5, -11.5), (11.5, 13.5)):
        s = s.fuse(cylz(4.0, z0, z1))
    keep = cq.Solid.makeCone(3.2, 4.1, 0.9, V(0, 0, -13.6), V(0, 0, 1))      # Axialfase, Anlaufring R 2.55..3.3
    s = s.cut(cylz(5.0, -13.6, -12.7).cut(keep))
    bore = cylz(2.75, -14, 14).intersect(box(-4, 4, -FLAT_D - 0.25, 4, -14, 14))   # D-Bohrung fuer Welle O5 mit Flaeche
    return one(s.cut(bore).clean())


def build_welle():
    s = cylz(2.5, -16.5, 13.7)                      # O5: Lagerzapfen -y + Sitz im Schneckenkoerper
    s = s.fuse(cylz(3.0, 13.6, SHAFT_END))          # O6: Lagerzapfen +y und Drehradsitz, Schulter am +y-Bund
    s = s.cut(box(-4, 4, -4, -FLAT_D, -17, SHAFT_END + 1))
    return one(s.clean())


def build_worm_fused():
    return cq.Compound.makeCompound([build_worm_koerper(), build_welle()])   # verklebt, 0.05 mm Fuegespalt


def welle_druckfertig(w):
    return on_bed(rot(rot(w, "y", 90), "x", 90))


if __name__ == "__main__" and os.environ.get("MODE") == "welle6":
    body, welle, hw = build_worm_koerper(), build_welle(), build_handwheel()
    print("Koerper", body.isValid(), round(body.Volume(), 1), "Welle", welle.isValid(), round(welle.Volume(), 1), "Drehrad", hw.isValid(), round(hw.Volume(), 1))
    export(on_bed(body), "winde_schnecke_koerper_4gang")
    export(welle_druckfertig(welle), "winde_welle_o6_4gang")
    export(on_bed(rot(hw, "x", 180)), "winde_drehrad_o6_4gang")
    export(on_bed(build_base()), "winde_gehaeuse_unterteil_lager_4gang")
    export(on_bed(rot(b3.build_cover(), "x", 180)), "winde_gehaeuse_deckel_lager_4gang")
    export(b3.worm_to_world(build_worm_fused()), "winde_schnecke_montage_4gang", stl=False)
    export(handwheel_to_world(hw), "winde_drehrad_montage_4gang", stl=False)
    raise SystemExit

if __name__ == "__main__":
    import time
    t0 = time.time()
    base = build_base(); print("Unterteil", base.isValid(), round(base.Volume(), 1), round(time.time() - t0, 1), flush=True)
    cover = build_cover(); print("Deckel   ", cover.isValid(), round(cover.Volume(), 1), flush=True)
    th, worm = build_worm(); print("Schnecke ", worm.isValid(), round(worm.Volume(), 1), flush=True)
    hw = build_handwheel(); print("Drehrad  ", hw.isValid(), round(hw.Volume(), 1), flush=True)

    worm_w = worm_to_world(worm)
    hw_w = handwheel_to_world(hw)
    for nm, sol in (("unterteil", base), ("deckel", cover), ("schnecke", worm_w), ("drehrad", hw_w)):
        export(sol, f"winde_{nm}_montage{WTAG}", stl=False)

    # Druckausrichtung
    export(on_bed(base), f"winde_gehaeuse_unterteil{WTAG}")
    export(on_bed(rot(cover, "x", 180)), f"winde_gehaeuse_deckel{WTAG}")
    export(on_bed(worm), f"winde_schnecke_stehend{WTAG}")      # stehend, kurzer Zapfen unten (Druckausrichtung)
    export(on_bed(rot(hw, "x", 180)), f"winde_drehrad{WTAG}")
    for f in sorted(os.listdir(OUT)):
        if f.startswith("winde_") and WTAG in f:
            print(f, os.path.getsize(f"{OUT}/{f}") // 1024, "kB")
    print("gesamt", round(time.time() - t0, 1), "s")
