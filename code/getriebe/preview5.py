"""Vorschaubilder der Winde: (1) Deckel abgenommen, (2) Schnitt durch die Radachse (y >= 0 bleibt)."""
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import os
os.environ.setdefault("NSTART","4")
import build4 as b
from build3 import V

wheel = cq.importers.importStep(f"{b.OUT}/schneckenrad_mit_trommel_4gang.step").val().Solids()[0]
base = b.build_base()
cover = b.build_cover()
th, worm = b.build_worm()
crank = b.build_handwheel()
worm_w = b.worm_to_world(worm)
crank_w = b.handwheel_to_world(crank)
pin = cq.Solid.makeCylinder(1.5, 24.0, V(0, 0, -15.9), V(0, 0, 1))

COL = {"base": (0.62, 0.64, 0.68), "cover": (0.70, 0.72, 0.76), "wheel": (0.90, 0.80, 0.45),
       "worm": (0.35, 0.60, 0.80), "crank": (0.85, 0.40, 0.35), "pin": (0.3, 0.3, 0.3)}


def tris(sol, tol=0.03, ang=0.3):
    v, t = sol.tessellate(tol, ang)
    Vv = np.array([[p.x, p.y, p.z] for p in v])
    return Vv[np.array(t)]


def draw(ax, items, light):
    allp, allc = [], []
    for name, sol in items:
        tr = tris(sol)
        n = np.cross(tr[:, 1] - tr[:, 0], tr[:, 2] - tr[:, 0])
        n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
        I = np.clip(n @ light, 0, 1) * 0.65 + 0.35
        allp.append(tr)
        allc.append(np.array(COL[name])[None, :] * I[:, None])
    P = np.concatenate(allp); C = np.concatenate(allc)
    ax.add_collection3d(Poly3DCollection(P, facecolors=C, linewidths=0, antialiaseds=False))


def fig(items, elev, azim, title, fn, lim, light):
    f = plt.figure(figsize=(9, 7)); ax = f.add_subplot(111, projection="3d")
    draw(ax, items, np.array(light) / np.linalg.norm(light))
    (x0, x1), (y0, y1), (z0, z1) = lim
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_zlim(z0, z1)
    ax.set_box_aspect((x1 - x0, y1 - y0, z1 - z0)); ax.view_init(elev=elev, azim=azim); ax.axis("off")
    ax.set_title(title, fontsize=10)
    f.tight_layout(); f.savefig(fn, dpi=110); plt.close(f)


fig([("base", base), ("wheel", wheel), ("worm", worm_w), ("crank", crank_w), ("pin", pin)],
    48, -62, "Winde V2 ohne Deckel: Unterteil mit Schlauchtülle, Rad mit Trommel, 4-gängige Schnecke, Drehrad",
    "winde4_ohne_deckel.png", ((-50, 40), (-26, 34), (-24, 24)), (0.3, -0.5, 0.8))

half = cq.Solid.makeBox(80, 60, 80, V(-40, 0, -40))
cut = [("base", base.intersect(half)), ("cover", cover.intersect(half)), ("wheel", wheel.intersect(half)),
       ("worm", worm_w.intersect(half)), ("pin", pin.intersect(half))]
fig(cut, 6, -90, "Schnitt durch die Radachse (Blick von -y)", "winde4_schnitt.png",
    ((-50, 40), (0, 34), (-24, 24)), (0.2, -0.9, 0.35))
print("ok")
