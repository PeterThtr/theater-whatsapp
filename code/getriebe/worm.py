"""Schnecke (ZA-Profil, trapezförmiger Axialschnitt) per Helix-Sweep.

Achse = +Z, rechtsgängig, 1 Gang, Mitte bei z=0 (von -L/2 bis +L/2).
Alle Maße in mm.
"""
import math
import cadquery as cq

M = 1.5            # Modul
ALPHA = 25.0       # axialer Eingriffswinkel
D1 = 12.0          # Teilkreis-Ø Schnecke
RP = D1 / 2
RT = RP + 1.0 * M          # Kopfkreis-Radius (7.5)
RF = RP - 1.2 * M          # Fußkreis-Radius (4.2)
PITCH = math.pi * M        # Steigung = Lead bei 1 Gang (4.712)
TAN_A = math.tan(math.radians(ALPHA))


def make_worm(length, tip_r=RT, extra_w=0.0, bore=None, ridge_extra_r=0.0):
    """Schnecke der Länge `length`, zentriert um z=0.

    extra_w:  zusätzliche Gangbreite auf dem Teilkreis (für den Fräser = Flankenspiel)
    tip_r:    Kopfkreis-Radius des Gewindegangs
    """
    wp = PITCH / 2 + extra_w            # Gangbreite auf dem Teilkreis
    r_in = RF - 0.6                     # Profil reicht in den Kern hinein
    hw_in = wp / 2 + (RP - r_in) * TAN_A
    hw_tip = wp / 2 - (tip_r - RP) * TAN_A
    assert hw_tip > 0.05, hw_tip
    assert 2 * hw_in < PITCH - 0.05, (2 * hw_in, PITCH)

    z0 = -length / 2 - 1.5 * PITCH      # Helix beginnt vor dem Ende, wird später beschnitten
    h = length + 3.0 * PITCH
    helix = cq.Wire.makeHelix(PITCH, h, r_in).translate(cq.Vector(0, 0, z0))
    pts = [(r_in, z0 - hw_in), (tip_r, z0 - hw_tip), (tip_r, z0 + hw_tip), (r_in, z0 + hw_in)]
    prof = cq.Workplane("XZ").polyline(pts).close()
    thread = prof.sweep(cq.Workplane(obj=helix), isFrenet=True)
    core = cq.Workplane("XY").workplane(offset=-length / 2).circle(RF).extrude(length)
    body = core.union(thread)
    clip = cq.Workplane("XY").workplane(offset=-length / 2).circle(tip_r + 0.01).extrude(length)
    body = body.intersect(clip)
    if bore:
        body = body.cut(cq.Workplane("XY").workplane(offset=-length / 2 - 1).circle(bore / 2).extrude(length + 2))
    return body


if __name__ == "__main__":
    import time
    t = time.time()
    w = make_worm(24.0, bore=4.0)
    s = w.val()
    print("valid", s.isValid(), "vol", round(s.Volume(), 1), "time", round(time.time() - t, 1))
    bb = s.BoundingBox()
    print("bbox", round(bb.xmin, 2), round(bb.xmax, 2), round(bb.zmin, 2), round(bb.zmax, 2))
    cq.exporters.export(w, "worm_test.step")
