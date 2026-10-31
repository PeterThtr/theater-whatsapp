"""Nachbau der automatischen 'Normal (auto)'-Ueberhangerkennung von Bambu Studio (SupportMaterial.cpp, detect_overhangs):

    diff = Schicht_n  -  expand(Schicht_n-1, h_unten / tan(Schwellenwinkel + 1 deg))
    Bereiche, die nach 0.1 * Linienbreite Erosion leer sind, werden verworfen.
    Danach wird der Ueberhang wieder um denselben Betrag aufgeweitet und auf (Schicht_n - Schicht_n-1) begrenzt.

Aufruf: python3 bs_support_sim.py <stl> <schichthoehe> [schwellenwinkel=30]
Die STL muss in Druckausrichtung vorliegen (z=0 = Druckbett, mm).
"""
import sys, math
import numpy as np
import trimesh
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union

FW = 0.42            # Linienbreite Aussenwand
FIRST_H = 0.2        # Hoehe der ersten Schicht (A1-Profile)
import os
DEBUG = bool(os.environ.get('DEBUG'))


def layers_geom(mesh, zs):
    """Alle Schnitte in EINEM festen 2D-Koordinatensystem (section_multiplane), sonst verschieben sich die Schichten gegeneinander."""
    secs = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(zs))
    out = []
    for sec in secs:
        if sec is None:
            out.append(Polygon())
            continue
        polys = sec.polygons_full
        out.append(unary_union(polys) if len(polys) else Polygon())
    return out


def main(path, h, thr):
    mesh = trimesh.load(path, force="mesh")
    zmin, zmax = mesh.bounds[0][2], mesh.bounds[1][2]
    mesh.apply_translation([0, 0, -zmin])
    H = zmax - zmin
    # Schichten
    prints = [FIRST_H]
    while prints[-1] < H - 1e-6:
        prints.append(prints[-1] + h)
    heights = [FIRST_H] + [h] * (len(prints) - 1)
    mids = [p - hh / 2 for p, hh in zip(prints, heights)]
    thr_eff = thr + 1.0
    layers = layers_geom(mesh, [min(z, H - 1e-4) for z in mids])
    total = 0.0
    flagged = []
    for n in range(1, len(layers)):
        lower, cur = layers[n - 1], layers[n]
        if cur.is_empty:
            continue
        off = heights[n - 1] / math.tan(math.radians(thr_eff))
        grown = lower.buffer(off) if not lower.is_empty else Polygon()
        diff = cur.difference(grown)
        if diff.is_empty:
            continue
        # Filter wie in BS: nach 0.1*fw Erosion muss etwas uebrig bleiben
        if diff.buffer(-0.1 * FW).is_empty:
            continue
        full = diff.buffer(off).intersection(cur).difference(lower)
        a = full.area
        if a > 0.02:
            flagged.append((prints[n], a, diff.area))
            if DEBUG:
                c = full.centroid
                print(f"   [debug] z={prints[n]:.2f} area={a:.2f} diff={diff.area:.3f} centroid r={math.hypot(c.x, c.y):.2f} bounds={[round(v,2) for v in full.bounds]}")
            total += a
    print(f"{path.split('/')[-1]}  h={h}  Schwelle={thr}° (wirksam {thr_eff}°)  Hoehe={H:.2f} mm  Schichten={len(layers)}")
    print(f"  Schichten mit Ueberhang: {len(flagged)}   Summe der Schichtflaechen: {total:.1f} mm²")
    if flagged:
        # nach z clustern
        clusters = []
        for z, a, d in flagged:
            if clusters and z - clusters[-1]["z1"] <= 1.5 * h + 1e-6:
                c = clusters[-1]; c["z1"] = z; c["n"] += 1; c["sum"] += a; c["max"] = max(c["max"], a)
            else:
                clusters.append({"z0": z, "z1": z, "n": 1, "sum": a, "max": a})
        for c in clusters[:14]:
            print(f"   z {c['z0']:.2f}..{c['z1']:.2f}  {c['n']} Schicht(en)  Summe {c['sum']:.1f} mm²  max {c['max']:.1f} mm²/Schicht")
        if len(clusters) > 14:
            print(f"   ... {len(clusters) - 14} weitere Bereiche, Summe {sum(c['sum'] for c in clusters[14:]):.1f} mm²")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]) if len(sys.argv) > 3 else 30.0)
