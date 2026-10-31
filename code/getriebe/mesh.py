import math, sys, time
import numpy as np
import cadquery as cq
import env

P=env.P; A=env.A; RP=env.RP; TA=env.TA

def worm_member(qx,qy,qz,phi_deg,wp,tip):
    xl=qx-A; yl=-qz; zl=qy
    rho=np.hypot(xl,yl); psi=np.degrees(np.arctan2(yl,xl))
    phase=zl-P*(psi-phi_deg)/360.0
    d=np.mod(phase+P/2,P)-P/2
    hw=wp/2+(RP-rho)*TA
    return np.minimum(hw-np.abs(d), tip-rho)>=0

def interference(sol, theta_deg, s, wp, tip, pts, a=A):
    qx,qy,qz=pts
    phi = s*env.Z2*theta_deg
    inw = worm_member(qx,qy,qz,phi,wp,tip)
    qx,qy,qz = qx[inw],qy[inw],qz[inw]
    th=math.radians(theta_deg)
    # Rad im Labor um +theta gedreht -> Punkt in Radkoordinaten: Rz(-theta)
    px= math.cos(th)*qx + math.sin(th)*qy
    py=-math.sin(th)*qx + math.cos(th)*qy
    cnt=0
    for x,y,z in zip(px,py,qz):
        if x*x+y*y>env.R_BLANK**2: continue
        if sol.isInside(cq.Vector(float(x),float(y),float(z)),1e-4): cnt+=1
    return cnt, len(qx)

if __name__=="__main__":
    sol = cq.importers.importStep("wheel_v1.step").val().Solids()[0]
    rng=np.random.default_rng(3)
    N=60000
    pts=(rng.uniform(4.5,14.0,N), rng.uniform(-11,11,N), rng.uniform(-3.0,3.0,N))
    for s in (+1,-1):
        for (name,wp,tip) in (("echt",P/2,7.5),("Fraeser",P/2+0.2,7.8)):
            res=[]
            for th in (0.0, 7.0, 13.0, 21.0, 30.0):
                c,n=interference(sol,th,s,wp,tip,pts)
                res.append(f"{th:g}°:{c}/{n}")
            print("sign",s,name," ".join(res), flush=True)
