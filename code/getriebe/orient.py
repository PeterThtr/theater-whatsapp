import numpy as np, cadquery as cq, build3 as b
th, worm = b.build_worm()
v,t = worm.tessellate(0.01,0.1)
V=np.array([[p.x,p.y,p.z] for p in v]); T=np.array(t); tr=V[T]
n=np.cross(tr[:,1]-tr[:,0], tr[:,2]-tr[:,0]); A=0.5*np.linalg.norm(n,axis=1); n/= (2*A[:,None]+1e-15)
def stats(R, name):
    nn=n@R.T; pts=tr@R.T
    zmin=pts[:,:,2].min(); zc=pts[:,:,2].mean(axis=1)
    down = nn[:,2] < 0
    ang = np.degrees(np.arcsin(np.clip(-nn[:,2],0,1)))   # Überhang gegen die Senkrechte
    on_bed = (pts[:,:,2].max(axis=1) < zmin+0.15) & (nn[:,2] < -0.9)
    bed = A[on_bed].sum()
    bad = (down) & (ang>45) & ~on_bed
    vbad = (down) & (ang>60) & ~on_bed
    print(f"{name:28s} Auflage {bed:6.1f} mm²  Überhang>45° {A[bad].sum():7.1f} mm²  >60° {A[vbad].sum():7.1f} mm²  von gesamt {A.sum():7.1f}")
def Ry(a):
    a=np.radians(a); return np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
stats(np.eye(3),"stehend (Achse senkrecht)")
for tilt in (20,45,70):
    stats(Ry(tilt),f"geneigt {tilt}°")
stats(Ry(90),"liegend (Achse waagerecht)")
stats(Ry(-90),"liegend, Fläche oben")
