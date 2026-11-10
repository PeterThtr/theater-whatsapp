import tele as t, cadquery as cq, trimesh, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
cols={"fuss":"#8a8a8a","seg1":"#5b7db1","seg2":"#d08a3a","seg3":"#5b7db1","seg4":"#d08a3a","seg5":"#5b7db1","seg6":"#d08a3a","ring2":"#2a9d6a","ring3":"#2a9d6a","ring4":"#2a9d6a","kappe":"#c0504d"}
fig,axs=plt.subplots(2,1,figsize=(13,6.2),gridspec_kw={"height_ratios":[1,1]})
for ax,ext in zip(axs,(False,True)):
    parts,_=t.assembly(ext)
    for n,p in parts.items():
        cq.exporters.export(cq.Workplane().add(p),"/tmp/_p.stl",tolerance=0.02)
        m=trimesh.load("/tmp/_p.stl")
        sec=m.section(plane_origin=[0,0,0],plane_normal=[0,1,0])
        if sec is None: continue
        for e in sec.discrete:
            ax.fill(e[:,2],e[:,0],color=cols[n],lw=0)
    # Feder und Schnur schematisch
    capb=_[t.N]+t.L+(t.KAPPE_MUFFE if t.KAPPE_BREIT else t.SHAFT_BOT)
    if t.DRAHT:
        ax.plot([-3,capb],[0,0],color="k",lw=1.4)          # Draht Ø 1,5 (schematisch)
    else:
        ax.plot([-3,capb],[0,0],color="k",lw=0.6,ls="--")
        for y in (4.6,-4.6): ax.plot([0,capb],[y,y],color="#999",lw=0.8,ls=":")
    ax.set_aspect("equal"); ax.set_ylim(-12,12) if t.DRAHT else ax.set_ylim(-25,25); ax.set_xlim(-4,265)
    ax.set_title(("Ausgefahren" if ext else "Eingefahren")+f" – Länge {max(p.BoundingBox().zmax for p in parts.values())+1.5:.0f} mm (Längsschnitt)",fontsize=10,loc="left")
    ax.set_yticks([]); ax.tick_params(labelsize=8)
axs[1].set_xlabel("mm ab Oberseite Fußplatte",fontsize=9)
plt.tight_layout(); plt.savefig("out/"+{"draht6":"nase_draht6_","draht2":"nase_draht2_","draht":"nase_draht_","feder2":"nase_feder2_"}.get(t.PROFIL,"nase_")+"schnitt.png",dpi=130)
# Detail Fuge
fig,ax=plt.subplots(figsize=(7,5))
parts,B=t.assembly(True)
for n in [q for q in ("seg2","seg3","ring2","seg1") if q in parts]:
    cq.exporters.export(cq.Workplane().add(parts[n]),"/tmp/_p.stl",tolerance=0.005)
    m=trimesh.load("/tmp/_p.stl"); sec=m.section(plane_origin=[0,0,0],plane_normal=[0,1,0])
    for e in sec.discrete: ax.fill(e[:,0],e[:,2],color=cols[n],lw=0)
ax.set_xlim((5.5,9.5) if t.DRAHT else (8.5,14.5)); ax.set_ylim(B[3]-2,B[2]+t.L+2.5); ax.set_aspect("equal")
ax.set_title("Detail ausgefahren: Segment 3 (blau) in Segment 2 (orange).\nBund von Seg. 3 liegt an der Lippe von Seg. 2 an"+(", Ring 2 grün" if t.RINGE else ""),fontsize=9)
ax.set_xlabel("Radius mm"); ax.set_ylabel("z mm")
plt.tight_layout(); plt.savefig("out/"+{"draht6":"nase_draht6_","draht2":"nase_draht2_","draht":"nase_draht_","feder2":"nase_feder2_"}.get(t.PROFIL,"nase_")+"detail.png",dpi=130)
