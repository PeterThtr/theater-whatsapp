import os
os.environ.setdefault("NSTART","4")
import numpy as np, cadquery as cq
import build4 as b, mesh2
from build3 import CORD_Y, CORD_Z, CAV_X0
base=b.build_base()
v,t=base.tessellate(0.01,0.2)
Vv=np.array([[p.x,p.y,p.z] for p in v]); T=np.array(t)
import vtk
from vtk.util.numpy_support import numpy_to_vtk
pts=vtk.vtkPoints(); pts.SetData(numpy_to_vtk(np.ascontiguousarray(Vv),deep=True))
cells=vtk.vtkCellArray()
for a,bb,c in T:
    cells.InsertNextCell(3); cells.InsertCellPoint(int(a)); cells.InsertCellPoint(int(bb)); cells.InsertCellPoint(int(c))
pd=vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
ins=mesh2.Inside(pd)
# Schnur: von der Trommel (x=0, y=CORD_Y, z=CORD_Z+dz) diagonal zum Lochmittelpunkt an der Schulter, dann gerade durch die Bohrung
for dz in (-1.65,-1.0,0.0,1.0,1.65):
    p0=np.array([0.0,CORD_Y,CORD_Z+dz]); p1=np.array([b.X_STOP,CORD_Y,CORD_Z])
    s1=np.linspace(0,1,300)[:,None]; seg1=p0+(p1-p0)*s1
    xs=np.linspace(b.X_STOP,b.OX0-b.FLANGE_L-b.NOZ_L-3,400)
    seg2=np.stack([xs,np.full_like(xs,CORD_Y),np.full_like(xs,CORD_Z)],1)
    pts_=np.vstack([seg1,seg2])
    print(f"Schnur ab Trommelnut-Versatz {dz:+.2f}: Punkte im Körper =", int(ins(pts_).sum()))
# Abstand der Schnur zur Lochwand an der Trichteröffnung (x=CAV_X0): Radius Trichter 1.8
for dz in (-1.65,1.65):
    z_at=CORD_Z+dz*(1-(0-CAV_X0)/(0-b.X_STOP))*(-1)  # nur zur Info
print("Trichter-Radius an der Kavität: 1.8 mm, Schnur ±1.65 mm Versatz an der Trommel -> am Trichter ca.", round(1.65*(b.X_STOP-CAV_X0)/(b.X_STOP-0),2), "mm")
