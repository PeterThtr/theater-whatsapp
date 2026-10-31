"""Mehrgängige Schnecke als verdrehte Extrusion des Stirnschnitts (keine Booleans nötig).

Achse +Z, rechtsgängig, NS Gänge (Umgebungsvariable NSTART), zentriert um z=0.
Axialschnitt: Trapez (ZA-Profil), Flankenwinkel ALPHA zur Radialen, axiale Teilung P = pi*m
(unabhängig von der Gangzahl).  Steigung (Lead) L = NS*P.
"""
import math
import numpy as np
import cadquery as cq
import env

M = env.M
ALPHA = env.ALPHA
D1 = env.D1
RP = D1 / 2
RT = RP + 1.0 * M      # 7.5
RF = RP - 1.2 * M      # 4.2
P = env.P              # axiale Teilung 4.712
NS = env.NS
L = env.L              # Steigung
TA = math.tan(math.radians(ALPHA))
WP = P / 2             # Gangbreite auf dem Teilkreis (ohne Spiel)


def hw(r, wp=WP):
    """Halbe Gangbreite (axial) bei Radius r."""
    return wp / 2 + (RP - r) * TA


def make_worm(length=24.0, bore=4.0, wp=WP, tip=RT, nflank=24):
    hw_tip = hw(tip, wp)
    hw_root = hw(RF, wp)
    psi_t = 360.0 * hw_tip / L            # Winkel Kopfland (halb)
    psi_r = 360.0 * hw_root / L           # Winkel Flankenende am Fuß (halb)
    assert psi_r < 180.0 / NS, f"Gänge überlappen im Fuß: {psi_r} >= {180.0 / NS}"
    psi0 = -360.0 * (length / 2) / L      # Phase der Gangmitte bei z = -L/2

    def pol(r, psi_deg):
        a = math.radians(psi_deg)
        return (r * math.cos(a), r * math.sin(a))

    def flank(c, sign):
        pts = []
        for k in range(nflank + 1):
            psi = psi_t + (psi_r - psi_t) * k / nflank
            r = RP + (wp / 2 - L * psi / 360.0) / TA
            pts.append(pol(r, c + sign * psi))
        return pts

    centers = [psi0 + 360.0 * k / NS for k in range(NS)]
    w = cq.Workplane("XY").workplane(offset=-length / 2)
    first = flank(centers[0], -1)[0]
    w = w.moveTo(*first)
    for k, c in enumerate(centers):
        f_pos = flank(c, +1)
        f_neg = flank(c, -1)
        c_next = centers[(k + 1) % NS] + (360.0 if k == NS - 1 else 0.0)
        fn_next = flank(c_next, -1)
        # Kopfbogen (Negativflanke -> Positivflanke)
        w = w.threePointArc(pol(RT, c), f_pos[0])
        # Positivflanke zum Fuß
        w = w.spline(f_pos[1:], includeCurrent=True)
        # Fußbogen zur nächsten Gangflanke
        w = w.threePointArc(pol(RF, 0.5 * (c + c_next)), fn_next[-1])
        # Negativflanke des nächsten Ganges nach oben
        w = w.spline(list(reversed(fn_next))[1:], includeCurrent=True)
    w = w.close()
    if bore:
        w = w.moveTo(0, 0).circle(bore / 2)
    twist = 360.0 * length / L
    return w.twistExtrude(length, twist)


if __name__ == "__main__":
    import time
    t = time.time()
    wk = make_worm(bore=None)
    s = wk.val()
    print("NS", NS, "valid", s.isValid(), "vol", round(s.Volume(), 1), "type", s.ShapeType(), "t", round(time.time() - t, 1))
    # Gangmitte bei Winkel psi liegt bei z = L*psi/360 + k*P (rechtsgängig)
    ok = True
    for psi in (0.0, 70.0, 130.0, 215.0, 300.0):
        for k in range(-1, 2):
            z = L * psi / 360.0 + k * P
            if abs(z) > 10:
                continue
            c = math.cos(math.radians(psi)); sn = math.sin(math.radians(psi))
            ins = s.isInside(cq.Vector(6.0 * c, 6.0 * sn, z))
            out = not s.isInside(cq.Vector(6.0 * c, 6.0 * sn, z + P / 2))
            if not (ins and out):
                ok = False
                print("FAIL", psi, k, ins, out)
    print("Gangmitte innen / Lücke außen:", "OK" if ok else "FEHLER")
    print("Kopf  (7.4) innen:", s.isInside(cq.Vector(7.4, 0, 0)), " (7.6) außen:", not s.isInside(cq.Vector(7.6, 0, 0)))
    cq.exporters.export(wk, f"out/schnecke_m1.5_{NS}gang_test.step")
