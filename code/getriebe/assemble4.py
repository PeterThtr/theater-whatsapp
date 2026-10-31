import os
os.environ.setdefault("NSTART","4")
import cadquery as cq, build4 as b
from build3 import V
wheel = cq.importers.importStep(f"{b.OUT}/schneckenrad_mit_trommel_4gang.step").val().Solids()[0]
base = b.build_base(); cover = b.build_cover()
th, worm = b.build_worm(); crank = b.build_handwheel()
pin = cq.Solid.makeCylinder(1.5, 24.0, V(0, 0, -15.9), V(0, 0, 1))
asm = cq.Assembly(name="winde")
for name, s, col in (("unterteil", base, (0.62, 0.64, 0.68)), ("deckel", cover, (0.75, 0.77, 0.80)),
                     ("rad_mit_trommel", wheel, (0.90, 0.80, 0.45)), ("schnecke_mit_welle", b.worm_to_world(worm), (0.35, 0.60, 0.80)),
                     ("drehrad", b.handwheel_to_world(crank), (0.85, 0.40, 0.35)), ("stahlstift_3x24", pin, (0.3, 0.3, 0.3))):
    asm.add(cq.Workplane(obj=s), name=name, color=cq.Color(*col))
asm.save(f"{b.OUT}/winde_baugruppe_4gang.step")
print("ok")
