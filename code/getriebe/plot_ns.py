import os, numpy as np
import env
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig,ax=plt.subplots(1,3,figsize=(15,4.8))
for z in (-3.0,0.0,3.0):
    beta,rs=env.outline(z,nbeta=360)
    land=(rs>=env.R_BLANK-1e-6).mean()
    print(f"NS={env.NS} z={z:+.1f} rmin={rs.min():.2f} rmax={rs.max():.2f} Kopfland={land*100:.0f}% der Teilung  Zahnmitte bei beta={beta[np.argmax(rs>=env.R_BLANK-1e-6)]:.1f}")
    ax[0].plot(beta,rs,label=f"z={z}")
    bb=np.concatenate([beta+36*k for k in range(env.Z2)]+[[360]]); rr=np.concatenate([rs]*env.Z2+[rs[:1]])
    ax[1].plot(rr*np.cos(np.radians(bb)),rr*np.sin(np.radians(bb)),lw=0.8,label=f"z={z}")
ax[0].legend(); ax[1].set_aspect("equal"); ax[1].legend()
# vergrößert: ein Zahn
for z in (-3.0,0.0,3.0):
    beta,rs=env.outline(z,nbeta=360)
    ax[2].plot(rs*np.cos(np.radians(beta)),rs*np.sin(np.radians(beta)),lw=1,label=f"z={z}")
ax[2].set_aspect("equal"); ax[2].set_xlim(4,9.5); ax[2].set_ylim(-1,6); ax[2].legend()
fig.suptitle(f"NS={env.NS}")
fig.savefig(f"outline_ns{env.NS}.png",dpi=100)
