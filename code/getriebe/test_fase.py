import os, time, sys
os.environ["NSTART"]="4"
import cadquery as cq, numpy as np
import build4 as b
t=time.time()
th0, w0 = b.build_worm(chamfer=False); print("ohne Fase: gültig", w0.isValid(), "Solids", len(w0.Solids()), "Vol", round(w0.Volume(),1), round(time.time()-t,1),"s", flush=True)
t=time.time()
th1, w1 = b.build_worm(chamfer=True);  print("mit  Fase: gültig", w1.isValid(), "Solids", len(w1.Solids()), "Vol", round(w1.Volume(),1), " Abtrag", round(w0.Volume()-w1.Volume(),1), "mm³", round(time.time()-t,1),"s", flush=True)
v,tt = w1.tessellate(0.01,0.2)
Vv=np.array([[p.x,p.y,p.z] for p in v]); r=np.hypot(Vv[:,0],Vv[:,1])
for z in (-11.9,-11.5,-10.5,-9.5,-8.9,-8.0,0.0):
    m=np.abs(Vv[:,2]-z)<0.12
    Rc=min(4.2+(z+12.0),7.5)
    print(f"z={z:6.1f}: größter Oberflächenradius {r[m].max():.2f}   Soll (Fase) {Rc:.2f}", flush=True)
