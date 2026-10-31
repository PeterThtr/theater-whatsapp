import math, sys, time, pickle
import numpy as np
import cadquery as cq
import env, wheel, worm2

t0=time.time()
wk, wires = wheel.make_wheel(bore=3.2)
ws = wk.val()
print("wheel solids", len(ws.Solids()), "valid", ws.isValid(), "vol", round(ws.Volume(),1), "t", round(time.time()-t0,1))
sol = ws.Solids()[0]
cq.exporters.export(cq.Workplane(obj=sol), "wheel_v1.step")

# 1) OCC-Solid gegen numerisches Modell an Zufallspunkten
rng = np.random.default_rng(1)
N=1500
r = rng.uniform(4.0, 9.3, N); b = rng.uniform(0, 2*np.pi, N); z = rng.uniform(-2.9, 2.9, N)
px, py = r*np.cos(b), r*np.sin(b)
rem = env.removed(px, py, z)
# numerisches Material: r<=9, nicht entfernt (Bohrung ignorieren, r>=4 hier)
num_in = (r <= env.R_BLANK) & (~rem)
occ_in = np.array([sol.isInside(cq.Vector(float(a), float(c), float(d)), 1e-4) for a,c,d in zip(px,py,z)])
mism = np.sum(num_in != occ_in)
print("Punkte", N, "Abweichungen OCC vs numerisch:", mism, f"({100*mism/N:.1f}%)")
pickle.dump((px,py,z,num_in,occ_in), open("cmp.pkl","wb"))
