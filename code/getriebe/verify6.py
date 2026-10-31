"""Baugruppenprüfung: Mindestabstände (Oberflächenpunkte, KD-Baum) und Durchdringung (Punkt-im-Netz)."""
import math, time, sys
import numpy as np
import cadquery as cq
from scipy.spatial import cKDTree
import os
os.environ.setdefault("NSTART","4")
import mesh2, build4 as b
from build3 import V

OUT = b.OUT


def tess(sol, tol=0.01, ang=0.2):
    v, t = sol.tessellate(tol, ang)
    return np.array([[p.x, p.y, p.z] for p in v]), np.array(t)


def sample_surface(Vv, T, n, rng):
    tr = Vv[T]
    a = 0.5 * np.linalg.norm(np.cross(tr[:, 1] - tr[:, 0], tr[:, 2] - tr[:, 0]), axis=1)
    idx = rng.choice(len(T), size=n, p=a / a.sum())
    u, v = rng.random(n), rng.random(n)
    f = u + v > 1
    u[f], v[f] = 1 - u[f], 1 - v[f]
    t = tr[idx]
    return t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])


def pd_from(Vv, T):
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk
    pts = vtk.vtkPoints(); pts.SetData(numpy_to_vtk(np.ascontiguousarray(Vv), deep=True))
    cells = vtk.vtkCellArray()
    for a, bb, c in T:
        cells.InsertNextCell(3); cells.InsertCellPoint(int(a)); cells.InsertCellPoint(int(bb)); cells.InsertCellPoint(int(c))
    pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
    return pd


rng = np.random.default_rng(11)
t0 = time.time()

wheel = cq.importers.importStep(f"{OUT}/schneckenrad_mit_trommel_4gang.step").val().Solids()[0]
base = b.build_base()
cover = b.build_cover()
worm = b.build_worm_fused()
crank = b.build_handwheel()
worm_w = b.worm_to_world(worm)
crank_w = b.handwheel_to_world(crank)
pin = cq.Solid.makeCylinder(1.5, 24.0, V(0, 0, -15.9), V(0, 0, 1))

parts = {"Rad+Trommel": wheel, "Unterteil": base, "Deckel": cover, "Schnecke": worm_w, "Drehrad": crank_w, "Stift": pin}
mesh = {k: tess(s, 0.01 if k != "Rad+Trommel" else 0.02) for k, s in parts.items()}
print("tess", round(time.time() - t0, 1), "s", {k: len(m[1]) for k, m in mesh.items()}, flush=True)
bb = {k: s.BoundingBox() for k, s in parts.items()}
for k, v in bb.items():
    print(f"{k:12s} x {v.xmin:7.2f}..{v.xmax:7.2f}  y {v.ymin:7.2f}..{v.ymax:7.2f}  z {v.zmin:7.2f}..{v.zmax:7.2f}")

samp = {k: sample_surface(*mesh[k], 120000, rng) for k in parts}
trees = {k: cKDTree(samp[k]) for k in parts}


def mind(a, b_):
    d, _ = trees[b_].query(samp[a], workers=2)
    i = d.argmin()
    return d.min(), samp[a][i]


pairs = [("Rad+Trommel", "Unterteil"), ("Rad+Trommel", "Deckel"), ("Rad+Trommel", "Schnecke"),
         ("Schnecke", "Unterteil"), ("Schnecke", "Deckel"), ("Drehrad", "Unterteil"), ("Drehrad", "Deckel"),
         ("Drehrad", "Schnecke"), ("Stift", "Unterteil"), ("Stift", "Deckel"), ("Stift", "Rad+Trommel"),
         ("Unterteil", "Deckel")]
print("\nMindestabstand der Oberflächen (mm):")
for a, b_ in pairs:
    d1, p1 = mind(a, b_)
    d2, p2 = mind(b_, a)
    d, p = (d1, p1) if d1 <= d2 else (d2, p2)
    print(f"  {a:12s} - {b_:12s}  {d:6.3f}   bei ({p[0]:.1f},{p[1]:.1f},{p[2]:.1f})", flush=True)

# Durchdringung: Zufallspunkte im Überlappungs-Quader, die in beiden Körpern liegen
print("\nDurchdringung (Punkte in beiden Körpern, von 0.5 Mio):")
ins = {k: mesh2.Inside(pd_from(*mesh[k])) for k in parts}
for a, b_ in pairs:
    A_, B_ = bb[a], bb[b_]
    lo = np.array([max(A_.xmin, B_.xmin), max(A_.ymin, B_.ymin), max(A_.zmin, B_.zmin)])
    hi = np.array([min(A_.xmax, B_.xmax), min(A_.ymax, B_.ymax), min(A_.zmax, B_.zmax)])
    if (hi <= lo).any():
        print(f"  {a:12s} - {b_:12s}  Quader überlappen nicht"); continue
    n = 500000
    pts = lo + rng.random((n, 3)) * (hi - lo)
    m = ins[a](pts)
    cnt = int(ins[b_](pts[m]).sum()) if m.any() else 0
    print(f"  {a:12s} - {b_:12s}  {cnt:6d}  (Überlappquader {np.round(hi-lo,1)})", flush=True)

# Schnurweg: Linie vom Kerntangentenpunkt (0,-10.25) nach -x durch den Schlauch; Nutbreite z -12.8..-9.5
print("\nSchnurweg (Punkte entlang der Linie in einem Körper):")
for dz in (-1.4, 0.0, +1.4):
    xs = np.linspace(-6.0, b.OX0 - 5.0, 400)
    pts = np.stack([xs, np.full_like(xs, b.CORD_Y), np.full_like(xs, b.CORD_Z + dz)], 1)
    hits = {k: int(ins[k](pts).sum()) for k in ("Rad+Trommel", "Unterteil", "Deckel")}
    print(f"  z-Versatz {dz:+.1f}: {hits}")
print("fertig", round(time.time() - t0, 1), "s")
