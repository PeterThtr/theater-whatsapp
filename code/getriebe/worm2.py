"""Schnecke als verdrehte Extrusion des Stirnschnitts (keine Booleans nötig).

Achse +Z, rechtsgängig, 1 Gang, zentriert um z=0.
Axialschnitt: Trapez (ZA-Profil), Flankenwinkel ALPHA zur Radialen.
"""
import math
import numpy as np
import cadquery as cq

M = 1.5
ALPHA = 25.0
D1 = 12.0
RP = D1 / 2
RT = RP + 1.0 * M      # 7.5
RF = RP - 1.2 * M      # 4.2
P = math.pi * M        # Steigung 4.712
TA = math.tan(math.radians(ALPHA))
WP = P / 2             # Gangbreite auf dem Teilkreis (ohne Spiel)


def hw(r, wp=WP):
    """Halbe Gangbreite (axial) bei Radius r."""
    return wp / 2 + (RP - r) * TA


def make_worm(length=24.0, bore=4.0, wp=WP, tip=RT, nflank=24):
    hw_tip = hw(tip, wp)
    hw_root = hw(RF, wp)
    psi_t = 360.0 * hw_tip / P            # Winkel Kopfland
    psi_r = 360.0 * hw_root / P           # Winkel Flankenende am Fuß
    psi0 = -360.0 * (length / 2) / P      # Phase der Gangmitte bei z = -L/2

    def pol(r, psi_deg):
        a = math.radians(psi_deg + psi0)
        return (r * math.cos(a), r * math.sin(a))

    # Flanke: r linear in psi (archimedische Spirale)
    def flank(sign):
        pts = []
        for k in range(nflank + 1):
            psi = psi_t + (psi_r - psi_t) * k / nflank
            r = RP + (wp / 2 - P * psi / 360.0) / TA
            pts.append(pol(r, sign * psi))
        return pts

    f_pos = flank(+1)
    f_neg = flank(-1)
    w = cq.Workplane("XY").workplane(offset=-length / 2)
    w = w.moveTo(*f_neg[0]).threePointArc(pol(tip, 0.0), f_pos[0])
    w = w.spline(f_pos[1:], includeCurrent=True)
    w = w.threePointArc(pol(RF, 180.0), f_neg[-1])
    w = w.spline(list(reversed(f_neg))[1:], includeCurrent=True)
    w = w.close()
    if bore:
        w = w.moveTo(0, 0).circle(bore / 2)
    twist = 360.0 * length / P
    return w.twistExtrude(length, twist)


if __name__ == "__main__":
    import time
    t = time.time()
    wk = make_worm()
    s = wk.val()
    print("valid", s.isValid(), "vol", round(s.Volume(), 1), "type", s.ShapeType(), "t", round(time.time() - t, 1))
    # Plausibilität: Ganzmitte bei z=0 -> Punkt (6,0,0) innen, (6,0,P/2) außen,
    # rechtsgängig: bei z=P/4 liegt die Gangmitte bei psi=+90 -> (0,6,P/4) innen
    tests = {
        "(6,0,0) innen": ((6, 0, 0), True),
        "(6,0,P/2) außen": ((6, 0, P / 2), False),
        "(0,6,P/4) innen": ((0, 6, P / 4), True),
        "(0,-6,P/4) außen": ((0, -6, P / 4), False),
        "(0,-6,-P/4) innen": ((0, -6, -P / 4), True),
        "(7.4,0,0) innen": ((7.4, 0, 0), True),
        "(7.6,0,0) außen": ((7.6, 0, 0), False),
        "(3,0,0) Bohrung": ((3, 0, 0), False),
        "(1,0,0) Bohrung": ((1, 0, 0), False),
    }
    for k, (p, exp) in tests.items():
        got = s.isInside(cq.Vector(*p))
        print(("OK  " if got == exp else "FAIL"), k, got)
    cq.exporters.export(wk, "worm2_test.step")
