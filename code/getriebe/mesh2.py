import math, sys, time
import numpy as np
import cadquery as cq
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
import env
P=env.P; A=env.A; RP=env.RP; TA=env.TA

def worm_member(qx,qy,qz,phi_deg,wp,tip):
    xl=qx-A; yl=-qz; zl=qy
    rho=np.hypot(xl,yl); psi=np.degrees(np.arctan2(yl,xl))
    phase=zl-env.L*(psi-phi_deg)/360.0
    d=np.mod(phase+P/2,P)-P/2
    hw=wp/2+(RP-rho)*TA
    return np.minimum(hw-np.abs(d), tip-rho)>=0

def polydata_from_solid(sol, tol=0.004, ang=0.15):
    v,t = sol.tessellate(tol, ang)
    pts=vtk.vtkPoints(); pts.SetData(numpy_to_vtk(np.array([[p.x,p.y,p.z] for p in v]),deep=True))
    cells=vtk.vtkCellArray()
    for a,b,c in t:
        cells.InsertNextCell(3); cells.InsertCellPoint(a); cells.InsertCellPoint(b); cells.InsertCellPoint(c)
    pd=vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(cells)
    return pd

class Inside:
    def __init__(self, pd):
        self.pd=pd
    def __call__(self, pts):
        p=vtk.vtkPoints(); p.SetData(numpy_to_vtk(np.ascontiguousarray(pts),deep=True))
        q=vtk.vtkPolyData(); q.SetPoints(p)
        f=vtk.vtkSelectEnclosedPoints(); f.SetInputData(q); f.SetSurfaceData(self.pd); f.SetTolerance(1e-6); f.CheckSurfaceOff(); f.Update()
        return vtk_to_numpy(f.GetOutput().GetPointData().GetArray("SelectedPoints")).astype(bool)

def interference(inside, theta_deg, s, wp, tip, pts):
    qx,qy,qz=pts
    phi=s*env.Z2*theta_deg/env.NS
    m=worm_member(qx,qy,qz,phi,wp,tip)
    qx,qy,qz=qx[m],qy[m],qz[m]
    th=math.radians(theta_deg)
    px= math.cos(th)*qx + math.sin(th)*qy
    py=-math.sin(th)*qx + math.cos(th)*qy
    keep = px*px+py*py <= (env.R_BLANK+0.05)**2
    P3=np.stack([px,py,qz],1)[keep]
    if len(P3)==0: return 0,0
    return int(inside(P3).sum()), len(P3)

if __name__=="__main__":
    step = sys.argv[1] if len(sys.argv)>1 else "wheel_v1.step"
    sol = cq.importers.importStep(step).val().Solids()[0]
    t=time.time(); pd=polydata_from_solid(sol); print("triangles", pd.GetNumberOfPolys(), "t", round(time.time()-t,1), flush=True)
    ins=Inside(pd)
    # Selbsttest Punkt-im-Netz
    print("Test Mitte(0,0,0) Bohrung:", ins(np.array([[0,0,0.0]]))[0], " Zahnkörper (5,0,0):", ins(np.array([[4.2,0.0,0.0]]))[0])
    rng=np.random.default_rng(3)
    N=400000
    pts=(rng.uniform(4.5,14.0,N), rng.uniform(-11,11,N), rng.uniform(-3.0,3.0,N))
    thetas=(0.0, 4.0, 9.0, 13.0, 18.0, 24.0, 30.0, 35.0)
    for s in (+1,-1):
        for name,wp,tip in (("echt",P/2,7.5),("echt+0.1",P/2+0.1,7.6),("Fraeser",P/2+0.2,7.8),("echt+0.4",P/2+0.4,7.5)):
            res=[]
            for th in thetas:
                c,n=interference(ins,th,s,wp,tip,pts)
                res.append(f"{c}")
            print("sign",s,f"{name:9s}","Treffer je Pose",res, flush=True)
