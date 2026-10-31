import math, time
import numpy as np, cadquery as cq
import mesh2, env
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
OUT="out"
sol = cq.importers.importStep(f"{OUT}/schneckenrad_mit_trommel_{env.NS}gang.step").val().Solids()[0]
pd = mesh2.polydata_from_solid(sol)
ins = mesh2.Inside(pd)
rng=np.random.default_rng(5)
N=500000
pts=(rng.uniform(4.0,15.0,N), rng.uniform(-11,11,N), rng.uniform(-9.5,3.5,N))
def interf(theta, s, wp, tip):
    qx,qy,qz=pts
    m=mesh2.worm_member(qx,qy,qz,s*env.Z2*theta/env.NS,wp,tip)
    qx,qy,qz=qx[m],qy[m],qz[m]
    th=math.radians(theta)
    px= math.cos(th)*qx+math.sin(th)*qy; py=-math.sin(th)*qx+math.cos(th)*qy
    P3=np.stack([px,py,qz],1)
    return int(ins(P3).sum()), len(P3)
P=env.P
for name,wp,tip in (("echt",P/2,7.5),("echt+0.1",P/2+0.1,7.6),("echt+0.4",P/2+0.4,7.5),("Kopf+0.7",P/2,8.2)):
    res=[interf(th,-1,wp,tip)[0] for th in (0.0,9.0,18.0,27.0,35.0)]
    print(f"{name:9s} Treffer je Drehstellung:", res, flush=True)

# Schnittbild (Halbschnitt y>=0 sichtbar, Blick von -Y)
half = sol.intersect(cq.Solid.makeBox(40,20,40, cq.Vector(-20,0,-20)))
v,t = half.tessellate(0.02,0.2)
Vv=np.array([[p.x,p.y,p.z] for p in v]); T=np.array(t); tr=Vv[T]
n=np.cross(tr[:,1]-tr[:,0], tr[:,2]-tr[:,0]); n/= (np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
I=np.clip(n@np.array([0.3,-0.8,0.5]),0,1)*0.7+0.3
col=np.array([(0.86,0.8,0.55)])*I[:,None]
fig=plt.figure(figsize=(8,6.5)); ax=fig.add_subplot(111,projection="3d")
ax.add_collection3d(Poly3DCollection(tr,facecolors=col,linewidths=0))
ax.set_xlim(-13,13); ax.set_ylim(-13,13); ax.set_zlim(-15,5); ax.set_box_aspect((26,26,20))
ax.view_init(elev=12, azim=-90); ax.axis("off"); ax.set_title("Halbschnitt durch die Radachse (Bohrung, Nut, Knotentasche, Schnurloch)",fontsize=10)
fig.tight_layout(); fig.savefig("section.png",dpi=110)
