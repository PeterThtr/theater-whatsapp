"""Numerische Hüllfläche des Schneckenrads (Simulation Wälzfräsen).

Radrahmen: Achse Z, Mittelebene z=0.  Schneckenachse liegt im Labor parallel Y durch (A,0,0).
Fräser = Schnecke mit Flankenspiel und größerem Kopfkreis (Kopfspiel).
Kinematik: Rad dreht um +Z um theta, Schnecke wandert dabei axial (+Y) um P*theta/(360/Z2)
(entspricht Drehung der rechtsgängigen Schnecke um -Z2*theta).
"""
import math
import os
import numpy as np

M = 1.5
ALPHA = 25.0
D1 = 12.0
RP = D1 / 2
P = math.pi * M
TA = math.tan(math.radians(ALPHA))
Z2 = 10
NS = int(os.environ.get("NSTART", "1"))   # Gangzahl der Schnecke
L = NS * P                    # Steigung (Lead)
A = (D1 + M * Z2) / 2          # 13.5
R_BLANK = M * Z2 / 2 + M       # 9.0
BACKLASH = float(os.environ.get("BACKLASH", "0.4"))   # zusätzliche Gangbreite des Fräsers auf dem Teilkreis (FDM-tauglich)
TIP_C = RP + 1.2 * M           # Fräserkopfradius 7.8 -> Radfußradius 5.7 in der Mittelebene
WP_C = P / 2 + BACKLASH


def margin(px, py, pz, theta_deg, sign=+1.0, wp=WP_C, tip=TIP_C):
    """Rand-Funktion >=0 heißt: Punkt (Radrahmen) liegt im Fräser bei Raddrehung theta.
    px,py,pz: Arrays (N,1); theta_deg: Array (1,K)."""
    th = np.radians(theta_deg)
    c, s = np.cos(th), np.sin(th)
    qx = c * px - s * py          # Rz(+theta) * p
    qy = s * px + c * py
    qz = pz
    xl = qx - A
    yl = -qz
    zl = qy - sign * P * theta_deg / (360.0 / Z2)   # axiale Koordinate relativ zur verschobenen Schnecke
    rho = np.hypot(xl, yl)
    psi = np.arctan2(yl, xl)
    phase = zl - L * psi / (2 * np.pi)
    d = np.mod(phase + P / 2, P) - P / 2
    hw = wp / 2 + (RP - rho) * TA
    return np.minimum(hw - np.abs(d), tip - rho)


def removed(px, py, pz, beta_theta_halfrange=60.0, step=0.1, sign=+1.0, chunk=3000):
    """Bool-Array: Punkt wird von irgendeiner Fräserstellung entfernt. px,py,pz: 1D."""
    n = len(px)
    out = np.zeros(n, dtype=bool)
    ang = np.degrees(np.arctan2(py, px))
    for i in range(0, n, chunk):
        sl = slice(i, i + chunk)
        # theta-Fenster um -beta
        k = np.arange(-beta_theta_halfrange, beta_theta_halfrange + step / 2, step)[None, :]
        th = -ang[sl][:, None] + k
        m = margin(px[sl][:, None], py[sl][:, None], pz[sl][:, None] if np.ndim(pz) else pz, th, sign)
        out[sl] = (m.max(axis=1) >= 0.0)
    return out


def outline(z, nbeta=360, r_lo=5.0, r_step=0.05, sign=+1.0):
    """Radialer Abstand der Materialgrenze r_s(beta) für beta in [0,36°)."""
    beta = np.linspace(0, 360.0 / Z2, nbeta, endpoint=False)
    rr = np.arange(r_lo, R_BLANK + 1e-9, r_step)
    B, R = np.meshgrid(beta, rr, indexing="ij")
    px = (R * np.cos(np.radians(B))).ravel()
    py = (R * np.sin(np.radians(B))).ravel()
    pz = np.full_like(px, z)
    rem = removed(px, py, pz, sign=sign).reshape(B.shape)
    rs = np.full(nbeta, R_BLANK)
    first = np.where(rem.any(axis=1), rem.argmax(axis=1), -1)
    for i in range(nbeta):
        j = first[i]
        if j < 0:
            continue
        if j == 0:
            rs[i] = r_lo
            continue
        lo, hi = rr[j - 1], rr[j]
        b = np.radians(beta[i])
        for _ in range(14):
            mid = 0.5 * (lo + hi)
            if removed(np.array([mid * math.cos(b)]), np.array([mid * math.sin(b)]), np.array([z]), sign=sign)[0]:
                hi = mid
            else:
                lo = mid
        rs[i] = 0.5 * (lo + hi)
    return beta, rs


if __name__ == "__main__":
    import time
    import json
    t = time.time()
    res = {}
    for z in (0.0, 3.0):
        beta, rs = outline(z)
        res[z] = (beta, rs)
        print("z", z, "rmin", round(rs.min(), 3), "rmax", round(rs.max(), 3), "t", round(time.time() - t, 1))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for z, (beta, rs) in res.items():
        ax[0].plot(beta, rs, label=f"z={z}")
    ax[0].set_xlabel("beta [deg]"); ax[0].set_ylabel("r [mm]"); ax[0].legend()
    # Polar-Darstellung der Zähne (10 Perioden)
    for z, (beta, rs) in res.items():
        bb = np.concatenate([beta + 36 * k for k in range(Z2)] + [[360]])
        rr = np.concatenate([rs] * Z2 + [rs[:1]])
        ax[1].plot(rr * np.cos(np.radians(bb)), rr * np.sin(np.radians(bb)), lw=0.8, label=f"z={z}")
    ax[1].set_aspect("equal"); ax[1].legend()
    fig.savefig("outline.png", dpi=110)
