#!/usr/bin/env python3
"""Stützwände bis zur Druckplatte unter frei hängenden, schmalen Rändern (für weiches TPU, das beim Druck schwingt).

Arbeitet auf der fertigen STL in Druckausrichtung (Z = Druckhöhe, Platte bei Z = 0):
  1. Raster in XY (Schritt d): tiefster Punkt der Unterseite je Rasterpunkt (Strahl von unten), nur wo die getroffene
     Fläche nach unten zeigt (Überhang) und höher als 0,6 mm über der Platte liegt.
  2. Davon nur die schmalen Bereiche (Ränder, Flügelkanten): breite Flächen (Öffnung mit Radius r_breit) bleiben dem
     Slicer überlassen.
  3. Unter jedem Rasterpunkt ein Säulchen von der Platte bis 0,3 mm in das Teil, zusammen eine Wand (mindestens
     2 Rasterpunkte breit). Nach dem Druck am Teil entlang abschneiden.
Optional nur unterhalb einer Höhe (--bis-z), z. B. nur der Bereich vor der Hülse.
Aufruf: python3 stuetzwand.py teil.stl ausgabe.stl [--bis-z 55] [--raster 0.5]
"""
import argparse, numpy as np, trimesh
from scipy import ndimage as ndi


def stuetzwand(m, d=0.5, r_breit=2.5, bis_z=1e9, z_min=0.6, n_unten=-0.35, einbett=0.3, umriss=False, frei_x=0.0):
    lo, hi = m.bounds
    xs = np.arange(lo[0] + d / 2, hi[0], d); ys = np.arange(lo[1] + d / 2, hi[1], d)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, lo[2] - 1.0)]
    r = np.tile([0.0, 0.0, 1.0], (len(o), 1))
    loc, idx_ray, idx_tri = m.ray.intersects_location(o, r, multiple_hits=False)
    zlow = np.full(X.size, np.nan); tri = np.full(X.size, -1)
    zlow[idx_ray] = loc[:, 2]; tri[idx_ray] = idx_tri
    zlow = zlow.reshape(X.shape); tri = tri.reshape(X.shape)
    ok = ~np.isnan(zlow)
    nz = np.where(tri >= 0, m.face_normals[np.clip(tri, 0, None), 2], 0).reshape(X.shape)
    if umriss:
        # nur am äußeren Umriss der Draufsicht (Zaun um das Teil), 2 Rasterpunkte breit
        voll = ndi.binary_fill_holes(ok)
        rand = voll & ~ndi.binary_erosion(voll, structure=ndi.generate_binary_structure(2, 2), iterations=2)
        cx = 0.5 * (lo[0] + hi[0])
        schmal = rand & ok & (zlow > lo[2] + z_min) & (zlow < bis_z) & (np.abs(X - cx) >= frei_x)
        schmal = ohne_loecher(m, schmal, X, Y, zlow, tri)
        return _saeulen(schmal, X, Y, zlow, lo, d, einbett, m)
    mask = ok & (zlow > lo[2] + z_min) & (nz < n_unten) & (zlow < bis_z)
    k = int(np.ceil(r_breit / d))
    st = ndi.generate_binary_structure(2, 1)
    breit = ndi.binary_opening(mask, structure=st, iterations=k)
    schmal = mask & ~ndi.binary_dilation(breit, structure=st, iterations=1)
    schmal = ndi.binary_dilation(schmal, structure=st, iterations=1) & ok & (zlow > lo[2] + z_min)
    # kleine Splitter weg
    lab, nlab = ndi.label(schmal)
    groesse = ndi.sum(schmal, lab, range(1, nlab + 1))
    for i, g in enumerate(groesse, 1):
        if g < 6:
            schmal[lab == i] = False
    return _saeulen(schmal, X, Y, zlow, lo, d, einbett, m)


def ohne_loecher(m, maske, X, Y, zlow, tri, r=6.0):
    """Säulen weglassen, deren Strahl in eine nach unten offene Bohrung läuft (z. B. Schlauchkanal am Stutzen):
    Vom Treffpunkt aus entlang der Flächennormale (in die Luft) liegt innerhalb r wieder Material."""
    ii, jj = np.nonzero(maske)
    if len(ii) == 0:
        return maske
    f = tri[ii, jj]
    n = m.face_normals[f]
    o = np.c_[X[ii, jj], Y[ii, jj], zlow[ii, jj]] + 0.05 * n
    loc, ir, _ = m.ray.intersects_location(o, n, multiple_hits=False)
    dist = np.linalg.norm(loc - o[ir], axis=1)
    weg = np.zeros(len(ii), bool); weg[ir[dist < r]] = True
    from scipy import ndimage as ndi
    loch = np.zeros_like(maske); loch[ii[weg], jj[weg]] = True
    loch = ndi.binary_dilation(loch, iterations=3)
    return maske & ~loch


def _saeulen(schmal, X, Y, zlow, lo, d, einbett, m=None):
    lab, nlab = ndi.label(schmal)
    for i, g in enumerate(ndi.sum(schmal, lab, range(1, nlab + 1)), 1):
        if g < 6:
            schmal[lab == i] = False
    ii, jj = np.nonzero(schmal)
    ein = np.full(len(ii), einbett)
    if m is not None and len(ii):
        # Einbettung höchstens 40 % der Materialdicke über dem Treffpunkt (sonst sticht die Säule in einen Kanal)
        o = np.c_[X[ii, jj], Y[ii, jj], zlow[ii, jj] + 0.01]
        loc, ir, _ = m.ray.intersects_location(o, np.tile([0.0, 0.0, 1.0], (len(o), 1)), multiple_hits=False)
        dick = np.full(len(ii), 10.0); dick[ir] = loc[:, 2] - o[ir, 2]
        ein = np.minimum(einbett, 0.4 * dick)
    import manifold3d as mf
    if not len(ii):
        return None, 0, 0.0
    wuerfel = []
    for (i, j, e) in zip(ii, jj, ein):
        h = zlow[i, j] + e - lo[2]
        wuerfel.append(mf.Manifold.cube([d * 1.02, d * 1.02, h], center=False)
                       .translate([X[i, j] - d * 0.51, Y[i, j] - d * 0.51, lo[2]]))
    W = mf.Manifold.batch_boolean(wuerfel, mf.OpType.Add)      # echte Vereinigung (überlappende Würfel)
    mm = W.to_mesh()
    wand = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts))
    return wand, int(len(ii)), float(len(ii) * d * d)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('ein'); ap.add_argument('aus')
    ap.add_argument('--bis-z', type=float, default=1e9); ap.add_argument('--raster', type=float, default=0.5)
    ap.add_argument('--breit', type=float, default=2.5)
    ap.add_argument('--umriss', action='store_true', help='nur Zaun am äußeren Umriss der Draufsicht')
    ap.add_argument('--frei-x', type=float, default=0.0, help='in der Mitte (|x| kleiner) keine Wand, z. B. vor der Nasenöffnung')
    a = ap.parse_args()
    m = trimesh.load(a.ein)
    w, n, flaeche = stuetzwand(m, d=a.raster, r_breit=a.breit, bis_z=a.bis_z, umriss=a.umriss, frei_x=a.frei_x)
    print(f'Wandpunkte {n}, Auflage {flaeche:.0f} mm²')
    r = trimesh.boolean.union([m, w], engine='manifold') if w is not None else m
    import sys, os
    sys.argv = [sys.argv[0], '--draht'] if '--draht' not in sys.argv else sys.argv
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from prothese import hauptkoerper                                     # Splitter weg, sauber vernetzen, STL-Prüfung
    r = hauptkoerper(r)
    print('wasserdicht', r.is_watertight, 'Körper', len(r.split(only_watertight=False)), 'Volumen', round(r.volume / 1000, 2), 'cm³ (vorher', round(m.volume / 1000, 2), ')')
    r.export(a.aus)
