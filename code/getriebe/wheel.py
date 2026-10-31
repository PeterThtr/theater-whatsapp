"""Schneckenrad aus gelofteten Querschnitten der numerischen Hüllfläche."""
import math
import sys
import numpy as np
import cadquery as cq
import env

Z2 = env.Z2
NB = 720                      # Punkte pro Zahnteilung (0.05°)
THR = 4.0                     # mm/° : Steilheit, ab der die Flanke in den 'radialen' Teil übergeht


def runs_circular(mask):
    """Liste (start,end) zusammenhängender True-Läufe auf kreisförmigem Array."""
    n = len(mask)
    starts = [i for i in range(n) if mask[i] and not mask[i - 1]]
    out = []
    for s in starts:
        e = s
        while mask[(e + 1) % n]:
            e += 1
        out.append((s, e % n))
    return out


def section_wire(z, nb=NB, n_flank=18, n_steep=14):
    beta, rs = env.outline(z, nbeta=nb)
    r_root = env.A - math.sqrt(env.TIP_C ** 2 - z ** 2)
    R = np.tile(rs, Z2)
    Bt = np.concatenate([beta + 360.0 / Z2 * k for k in range(Z2)])
    n = len(R)
    land = R >= env.R_BLANK - 1e-6
    root = R <= r_root + 2e-3
    X = R * np.cos(np.radians(Bt))
    Y = R * np.sin(np.radians(Bt))
    slope = np.abs(np.diff(R, append=R[0])) / (np.diff(Bt, append=Bt[0] + 360.0))

    tips = runs_circular(land)
    roots = runs_circular(root)
    assert len(tips) == Z2 and len(roots) == Z2, (z, len(tips), len(roots))
    tips.sort()
    roots.sort()

    def idx_range(a, b):
        return [(i % n) for i in range(a, (b if b >= a else b + n) + 1)]

    def resample(ids, k):
        pts = np.array([[X[i], Y[i]] for i in ids])
        seg = np.hypot(*np.diff(pts, axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        if s[-1] < 1e-9:
            raise RuntimeError("leeres Segment")
        t = np.linspace(0, s[-1], k)
        xs = np.interp(t, s, pts[:, 0])
        ys = np.interp(t, s, pts[:, 1])
        return [cq.Vector(float(a), float(b), z) for a, b in zip(xs, ys)]

    def arc(i0, i1, r):
        b0, b1 = Bt[i0], Bt[i1] if i1 >= i0 else Bt[i1] + 360.0
        bm = 0.5 * (b0 + b1)
        f = lambda b: cq.Vector(r * math.cos(math.radians(b)), r * math.sin(math.radians(b)), z)
        # Endpunkte exakt auf den tatsächlichen Gitterpunkten (Anschluss an die Splines)
        return cq.Edge.makeThreePointArc(cq.Vector(float(X[i0]), float(Y[i0]), z), f(bm),
                                         cq.Vector(float(X[i1]), float(Y[i1]), z))

    edges = []
    for k, (s, e) in enumerate(tips):
        s_next = tips[(k + 1) % Z2][0]
        # zugehöriger Fuß-Lauf: erster, der nach e beginnt
        r0, r1 = None, None
        for (a, b) in roots:
            if ((a - e) % n) < ((s_next - e) % n):
                r0, r1 = a, b
                break
        assert r0 is not None
        # Ecke C1 : erster Index ab e mit Steilheit > THR
        c1 = None
        for i in idx_range(e, r0):
            if slope[i] > THR:
                c1 = i
                break
        if c1 is None:        # keine Ecke -> bei 80 % der Flanke teilen (gleiche Topologie)
            c1 = (e + int(0.8 * ((r0 - e) % n))) % n
            if k == 0:
                print(f"  z={z:+.2f}: keine Ecke C1 (Zahn {k}), geteilt bei Index {c1}", file=sys.stderr)
        # Ecke C2 : letzter Index vor s_next (rückwärts ab s_next) mit Steilheit > THR
        c2 = None
        for i in reversed(idx_range(r1, s_next)):
            if slope[(i - 1) % n] > THR:
                c2 = i
                break
        if c2 is None:
            c2 = (r1 + int(0.2 * ((s_next - r1) % n))) % n
            if k == 0:
                print(f"  z={z:+.2f}: keine Ecke C2 (Zahn {k}), geteilt bei Index {c2}", file=sys.stderr)
        edges.append(arc(s, e, env.R_BLANK))
        edges.append(cq.Edge.makeSpline(resample(idx_range(e, c1), n_flank)))
        edges.append(cq.Edge.makeSpline(resample(idx_range(c1, r0), n_steep)))
        edges.append(arc(r0, r1, r_root))
        edges.append(cq.Edge.makeSpline(resample(idx_range(r1, c2), n_steep)))
        edges.append(cq.Edge.makeSpline(resample(idx_range(c2, s_next), n_flank)))
    return cq.Wire.assembleEdges(edges)


def make_wheel(b=6.0, bore=3.2, nsec=5):
    zs = np.linspace(-b / 2, b / 2, nsec)
    wires = [section_wire(float(z)) for z in zs]
    solid = cq.Solid.makeLoft(wires, False)
    wk = cq.Workplane(obj=solid)
    if bore:
        hole = cq.Workplane("XY").workplane(offset=-b / 2 - 1).circle(bore / 2).extrude(b + 2)
        wk = wk.cut(hole)
    return wk, wires


if __name__ == "__main__":
    import time
    t = time.time()
    wk, wires = make_wheel()
    s = wk.val()
    print("valid", s.isValid(), "vol", round(s.Volume(), 1), s.ShapeType(), "nfaces", len(s.Faces()), "t", round(time.time() - t, 1))
    cq.exporters.export(wk, "wheel_test.step")
