import os
"""Rad + Nabe + Trommel in einem Stück.  Koordinaten wie bisher: Radachse = Z, Radmitte z=0."""
import math, os, sys
import numpy as np
import cadquery as cq
import env, wheel

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
V = cq.Vector

B = 6.0                 # Radbreite
Z_WB = -B / 2           # Radunterseite
CONE_H = 2.0            # 45°-Kegel unter dem Rad (r 4 -> 6)
HUB_H = 5.5             # Nabe inkl. Kegel (1 mm Luft zwischen Schnecke und oberem Flansch)
FL = 1.0                # Flanschdicke
CORE_H = 3.3            # Kernhöhe (Schnurbreite)
R_HUB, R_CORE, R_FL = 4.0, 10.0, 12.0
R_CONE_TOP = 6.0
BORE = float(sys.argv[1]) if len(sys.argv) > 1 else 3.2
TAG = "" if BORE == 3.2 else f"_bohrung{BORE:g}"
if env.NS != 1:
    TAG += f"_{env.NS}gang"

z_hub_top = Z_WB
z_hub_bot = z_hub_top - HUB_H            # -8.5
z_flA_bot = z_hub_bot - FL               # -9.5
z_core_bot = z_flA_bot - CORE_H          # -12.8
z_flB_bot = z_core_bot - FL              # -13.8

def cyl(r, z0, h, x=0.0, y=0.0):
    return cq.Solid.makeCylinder(r, h, V(x, y, z0), V(0, 0, 1))

def build():
    wk, _ = wheel.make_wheel(b=B, bore=None)
    w = wk.val()
    w = w.Solids()[0] if hasattr(w, "Solids") and w.Solids() else w
    vol_w = w.Volume()

    parts = {
        "Flansch unten": cyl(R_FL, z_flB_bot, FL),
        "Kern": cyl(R_CORE, z_core_bot, CORE_H),
        "Flansch oben": cyl(R_FL, z_flA_bot, FL),
        "Nabe": cyl(R_HUB, z_hub_bot, HUB_H - CONE_H),
        "Kegel": cq.Solid.makeCone(R_HUB, R_CONE_TOP, CONE_H, V(0, 0, z_hub_top - CONE_H), V(0, 0, 1)),
        "Anker im Rad": cyl(5.5, Z_WB, 1.5),          # reicht in den Radkörper (r<Fußkreis 5.7)
    }
    exp_vol = vol_w
    body = w
    for name, p in parts.items():
        before = body.Volume()
        body = body.fuse(p)
        if name != "Anker im Rad":
            exp_vol += p.Volume()
        print(f"  + {name:14s} Vol {p.Volume():8.1f}   Körper {before:8.1f} -> {body.Volume():8.1f}", flush=True)
    # Bohrung
    body = body.cut(cyl(BORE / 2, z_flB_bot - 1, (B / 2) - z_flB_bot + 2))
    # Schnurloch (schräg, geradlinig durchfädelbar) + Knotentasche an der Unterseite
    zg = (z_flA_bot + z_core_bot) / 2                # Mitte der Schnurnut
    p1 = np.array([R_CORE, 0.0, zg])
    p2 = np.array([7.0, 0.0, z_flB_bot])
    d = p2 - p1; L = np.linalg.norm(d); d /= L
    start = p1 - d * 0.6
    hole = cq.Solid.makeCylinder(0.75, L + 1.6, V(*start), V(*d))
    pocket = cyl(2.0, z_flB_bot - 0.1, 1.3, x=7.0)
    body = body.cut(hole).cut(pocket)
    return body, exp_vol

if __name__ == "__main__":
    body, exp_vol = build()
    sol = body.Solids() if hasattr(body, "Solids") else [body]
    print("Solids:", len(sol), "valid:", body.isValid(), "Vol:", round(body.Volume(), 1), "(Summe Teile ohne Überlappung:", round(exp_vol, 1), ")")
    s = sol[0] if len(sol) == 1 else max(sol, key=lambda q: q.Volume())
    cq.exporters.export(cq.Workplane(obj=s), f"{OUT}/schneckenrad_mit_trommel{TAG}.step")
    cq.exporters.export(cq.Workplane(obj=s), f"{OUT}/schneckenrad_mit_trommel{TAG}.stl", tolerance=0.004, angularTolerance=0.05)
    print("Bohrung", BORE, "| Test Mitte frei:", not s.isInside(V(0, 0, -7), 1e-5), "| Wand bei r=1.5 voll:", s.isInside(V(BORE / 2 + 0.1, 0, -7), 1e-5))
    bb = s.BoundingBox()
    print("BBox z:", round(bb.zmin, 2), round(bb.zmax, 2), "Höhe", round(bb.zmax - bb.zmin, 2), "Ø", round(bb.xmax - bb.xmin, 2))
    for f in ("schneckenrad_mit_trommel.step", "schneckenrad_mit_trommel.stl"):
        print(f, os.path.getsize(f"{OUT}/{f}") // 1024, "kB")
