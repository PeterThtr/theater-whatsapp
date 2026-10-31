import numpy as np, cadquery as cq, sys
names = sys.argv[1:]
for name in names:
    s = cq.importers.importStep(f"out/{name}.step").val().Solids()[0]
    v,t = s.tessellate(0.01,0.1)
    V=np.array([[p.x,p.y,p.z] for p in v]); T=np.array(t); tr=V[T]
    n=np.cross(tr[:,1]-tr[:,0], tr[:,2]-tr[:,0]); A=0.5*np.linalg.norm(n,axis=1); n/= (2*A[:,None]+1e-15)
    zmin=tr[:,:,2].min()
    flat=(tr[:,:,2].max(axis=1)<zmin+0.05)&(n[:,2]<-0.99)
    down=(n[:,2]<-0.707)&~flat      # steiler als 45° überhängend, nicht Druckbett
    print(f"\n{name}: Auflagefläche {A[flat].sum():.0f} mm², Überhang >45°: {A[down].sum():.1f} mm²")
    # nach Höhe gruppieren (Zentroid z, gerundet)
    zc=tr[:,:,2].mean(axis=1)
    for z in np.unique(np.round(zc[down],1)):
        m=down&(np.round(zc,1)==z)
        c=tr[m].mean(axis=(0,1))
        print(f"   z={z:6.1f}  Fläche {A[m].sum():6.1f} mm²   bei x={c[0]:.1f} y={c[1]:.1f}   mittlere Normale z={n[m][:,2].mean():.2f}")
