import os
os.environ["NSTART"]="4"
import numpy as np, cadquery as cq
import build4 as b
th, worm = b.build_worm()
v,t = worm.tessellate(0.01, 0.1)
V = np.array([[p.x,p.y,p.z] for p in v]); T=np.array(t); tr=V[T]
n = np.cross(tr[:,1]-tr[:,0], tr[:,2]-tr[:,0]); A = 0.5*np.linalg.norm(n,axis=1); n /= (2*A[:,None]+1e-15)
rc = np.hypot(tr[:,:,0], tr[:,:,1]).mean(axis=1)

def Rx(a):
    a=np.radians(a); return np.array([[1,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
def Ry(a):
    a=np.radians(a); return np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])

def stats(R, name):
    nn = n@R.T; pts = tr@R.T
    zmin = pts[:,:,2].min()
    on_bed = (pts[:,:,2].max(axis=1) < zmin+0.15) & (nn[:,2] < -0.9)
    ang = np.degrees(np.arcsin(np.clip(-nn[:,2],0,1)))      # Überhang gegen die Senkrechte
    down = (nn[:,2] < 0) & ~on_bed
    out = [f"{name:34s} Auflage {A[on_bed].sum():6.1f} mm²"]
    for lim in (45, 55, 60, 80):
        out.append(f">{lim}°: {A[down & (ang>lim)].sum():6.1f}")
    print("  ".join(out))
    return nn, pts, ang, down, on_bed

print("Fläche gesamt:", round(A.sum()), "mm²\n")
stats(np.eye(3), "stehend, kurzer Zapfen unten")
stats(Rx(180), "stehend, lange Welle unten")
stats(Ry(90), "liegend (Achse waagerecht)")
stats(Ry(-90), "liegend, andere Seite")
stats(Ry(45), "geneigt 45°")

# Flankenwinkel im stehenden Zustand: nur Gewindeflanken (Radius 4.3..7.4, Normale nicht senkrecht)
nn, pts, ang, down, on_bed = stats(np.eye(3), "stehend (Detail)")
zc = tr[:,:,2].mean(axis=1)
flank = down & (rc>4.3) & (rc<7.45) & (np.abs(nn[:,2])<0.95) & (zc>-11.8) & (zc<11.8)
print("\nGewindeflanken (abwärts gerichtet): Fläche", round(A[flank].sum()), "mm², Überhang gegen Senkrechte: min/mittel/max =",
      round(ang[flank].min(),1), round(np.average(ang[flank],weights=A[flank]),1), round(ang[flank].max(),1))
for lo,hi in ((4.3,5.5),(5.5,6.5),(6.5,7.45)):
    m=flank&(rc>=lo)&(rc<hi)
    if m.any(): print(f"   r {lo}-{hi}: Überhang {np.average(ang[m],weights=A[m]):.1f}°  (Steigung gegen Waagerechte {90-np.average(ang[m],weights=A[m]):.1f}°)")
# übrige Überhänge >60° (Stirnflächen, Bund)
rest = down & (ang>60) & ~flank
zs = np.round(zc[rest],0)
print("\nÜberhänge >60° außerhalb der Flanken, nach Höhe (stehend):")
for z in np.unique(zs):
    m = rest & (np.round(zc,0)==z)
    print(f"   z={z:6.1f}  {A[m].sum():6.1f} mm²   Radius {rc[m].min():.1f}..{rc[m].max():.1f}")
