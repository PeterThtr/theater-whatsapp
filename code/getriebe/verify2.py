import math, time
import numpy as np, cadquery as cq
import mesh2, env
OUT="out"
V=cq.Vector
sol = cq.importers.importStep(f"{OUT}/schneckenrad_mit_trommel.step").val().Solids()[0]
print("valid", sol.isValid(), "vol", round(sol.Volume(),1))
# Punktproben (Material ja/nein)
checks = {
 "Bohrung Mitte (0,0,-7)": ((0,0,-7), False),
 "Nabe (3.5,0,-7)": ((3.5,0,-7), True),
 "Kern (9,0,-11)": ((9,-0.5,-11), True),
 "Nut (11,0,-11) leer": ((11,0,-11), False),
 "Flansch unten (11.5,0,-13.3)": ((11.5,0,-13.3), True),
 "Flansch oben (11.5,0,-9.0)": ((11.5,0,-9.0), True),
 "Kegel (5.0,0,-3.5)": ((5.0,0,-3.5), True),
 "Luft neben Nabe (5,0,-7)": ((5,0,-7), False),
 "Radkörper (7,0,0)? (Zahn/Lücke)": None,
 "Knotentasche (7,0,-13.4)": ((7,0,-13.4), False),
 "Schnurloch Mitte (9.0,0,-12.0)": ((9.0,0,-11.95), False),
}
for k,v in checks.items():
    if v is None: continue
    p,exp=v; got=sol.isInside(V(*p),1e-5)
    print(("OK  " if got==exp else "FAIL"), k, got)

# Abstand Unterbau <-> Schnecken-Kopfzylinder (konservativ)
worm_cyl = cq.Solid.makeCylinder(7.5, 24.0, V(env.A, -12.0, 0.0), V(0,1,0))   # Achse parallel Y, Mitte z=0
below = cq.Solid.makeBox(40,40,13.8-3.0, V(-20,-20,-13.8)).intersect(sol)    # alles unterhalb Radunterseite
d = below.distance(worm_cyl) if hasattr(below,'distance') else None
print("kleinster Abstand Trommel/Nabe/Kegel <-> Schnecken-Kopfzylinder Ø15:", round(d,3), "mm")
