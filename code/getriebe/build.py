"""Erzeugt die endgültigen STEP-Dateien: Schnecke, Schneckenrad, Baugruppe + Vorschau."""
import math
import numpy as np
import cadquery as cq
import env, wheel, worm2

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
import os
os.makedirs(OUT, exist_ok=True)

# --- Schnecke
worm_wp = worm2.make_worm(length=24.0, bore=4.0)
worm_solid = worm_wp.val()

# --- Rad
wheel_wp, _ = wheel.make_wheel(b=6.0, bore=3.2)
wheel_solid = wheel_wp.val().Solids()[0]

print("Schnecke: valid", worm_solid.isValid(), "Vol", round(worm_solid.Volume(), 1))
print("Rad:      valid", wheel_solid.isValid(), "Vol", round(wheel_solid.Volume(), 1))

cq.exporters.export(cq.Workplane(obj=worm_solid), f"{OUT}/schnecke_m1.5_1gang_rechts.step")
cq.exporters.export(cq.Workplane(obj=wheel_solid), f"{OUT}/schneckenrad_m1.5_z10.step")

# --- Baugruppe in Eingriffslage (Rad-Achse = Z, Schnecken-Achse parallel Y im Abstand A)
worm_pos = worm_solid.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), -90).translate(cq.Vector(env.A, 0, 0))
asm = cq.Assembly(name="schneckengetriebe")
asm.add(cq.Workplane(obj=wheel_solid), name="schneckenrad", color=cq.Color(0.86, 0.80, 0.55))
asm.add(cq.Workplane(obj=worm_pos), name="schnecke", color=cq.Color(0.45, 0.62, 0.78))
asm.save(f"{OUT}/schneckengetriebe_baugruppe.step")
print("exportiert:", sorted(os.listdir(OUT)))
