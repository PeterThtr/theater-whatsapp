import itertools, time
import cadquery as cq
import tele as t
for ext in (False, True):
    parts, B = t.assembly(extended=ext)
    print("AUSGEFAHREN" if ext else "EINGEFAHREN", {k: round(v, 2) for k, v in B.items()})
    zs = [p.BoundingBox() for p in parts.values()]
    print("  Länge über alles inkl. Fussplatte: %.2f" % (max(b.zmax for b in zs) - min(b.zmin for b in zs)))
    names = list(parts)
    for a, b in itertools.combinations(names, 2):
        A, Bb = parts[a], parts[b]
        ba, bb = A.BoundingBox(), Bb.BoundingBox()
        if ba.zmax < bb.zmin - 0.5 or bb.zmax < ba.zmin - 0.5: continue
        v = A.intersect(Bb).Volume()
        d = A.distance(Bb) if v < 1e-6 else 0.0
        if v > 1e-4 or d < 0.3:
            print(f"  {a:6s}-{b:6s}  Durchdringung {v:8.4f} mm³   Abstand {d:.3f}")
