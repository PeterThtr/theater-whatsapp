import numpy as np, cadquery as cq
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
OUT="out"
w = cq.importers.importStep(f"{OUT}/schnecke_m1.5_1gang_rechts.step").val()
r = cq.importers.importStep(f"{OUT}/schneckenrad_m1.5_z10.step").val()
a = cq.importers.importStep(f"{OUT}/schneckengetriebe_baugruppe.step")
print("Schnecke", w.ShapeType(), w.isValid(), round(w.Volume(),1))
print("Rad", r.ShapeType(), r.isValid(), round(r.Volume(),1))
sols = a.vals()[0].Solids() if a.vals() else []
print("Baugruppe: Solids", len(sols), [round(s.Volume(),1) for s in sols])
for s in sols:
    c = s.Center(); print("  Schwerpunkt", round(c.x,2), round(c.y,2), round(c.z,2))
def tris(shape, tol=0.02):
    v,t = shape.tessellate(tol, 0.2)
    V=np.array([[p.x,p.y,p.z] for p in v]); T=np.array(t)
    return V[T]
def shade(tr, light=np.array([0.4,-0.5,0.8]), base=(0.8,0.78,0.7)):
    n=np.cross(tr[:,1]-tr[:,0], tr[:,2]-tr[:,0]); n/= (np.linalg.norm(n,axis=1,keepdims=True)+1e-12)
    l=light/np.linalg.norm(light); I=np.clip(n@l,0,1)*0.75+0.25
    return np.array(base)[None,:]*I[:,None]
fig=plt.figure(figsize=(13,5.2))
# 1) Rad von oben
ax=fig.add_subplot(1,3,1); ax.set_title("Schneckenrad, Draufsicht", fontsize=10)
tr=tris(r); top=tr[(tr[:,:,2]>2.99).all(axis=1)]
for t in top: ax.fill(t[:,0],t[:,1],color=(0.8,0.75,0.55),lw=0)
ax.set_aspect("equal"); ax.set_xlim(-10,10); ax.set_ylim(-10,10); ax.axis("off")
# 2) Baugruppe schräg
for k,(el,az,title) in enumerate(((28,-50,"Baugruppe, schräg"),(90,-90,"Baugruppe, Draufsicht (Blick auf Radachse)"))):
    ax=fig.add_subplot(1,3,2+k,projection="3d"); ax.set_title(title,fontsize=10)
    for s,col in ((sols[0],(0.86,0.78,0.5)),(sols[1],(0.45,0.62,0.78))):
        tr=tris(s,0.03)
        pc=Poly3DCollection(tr, facecolors=shade(tr,base=col), linewidths=0)
        ax.add_collection3d(pc)
    ax.set_xlim(-10,24); ax.set_ylim(-17,17); ax.set_zlim(-17,17)
    ax.set_box_aspect((34,34,34)); ax.view_init(elev=el, azim=az); ax.axis("off")
fig.tight_layout(); fig.savefig("preview.png", dpi=105)
