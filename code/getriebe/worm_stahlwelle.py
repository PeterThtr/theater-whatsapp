import os
os.environ["NSTART"]="4"
import cadquery as cq
import worm3, build4 as b4
from build3 import V, cylz, on_bed, export
th = worm3.make_worm(length=24.0, bore=None).val()
ring = cylz(9.0, -12.1, -8.6).cut(cq.Solid.makeCone(4.1, 7.6, 3.5, V(0,0,-12.1), V(0,0,1)))
s = th.cut(ring)
for z0,z1 in ((-13.5,-11.5),(11.5,13.5)):
    s = s.fuse(cylz(4.0,z0,z1))
keep = cq.Solid.makeCone(2.7, 4.1, 1.4, V(0,0,-13.6), V(0,0,1))
s = s.cut(cylz(5.0,-13.6,-12.2).cut(keep))
s = s.cut(cylz(2.0,-14,14))          # Bohrung fuer 4-mm-Stahlwelle
s = s.clean()
print("valid", s.isValid(), len(s.Solids()), round(s.Volume(),1))
export(on_bed(s), "winde_schnecke_fuer_stahlwelle_4gang")
