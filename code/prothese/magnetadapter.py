#!/usr/bin/env python3
"""Magnet-Adapter zwischen TPU-Kappe (Steckhülse) und PLA-Schaft der Steck-Nase (17.11.).

Statt den Schaft in die Kappe zu stecken, heften zwei Magnete 3 × 2 mm (Ø 3, 2 hoch) die Teile aneinander:
  A (Kappe):  Zapfen Ø 12,4 (wie der Schaftzapfen, 0,4 Pressung in der TPU-Bohrung Ø 12,0 × 12), 13 lang, steht
              also 1 mm aus der Hülse heraus. Dieser 1-mm-Bund zentriert und hält gegen Verrutschen.
  B (Schaft): Muffe für den Schaftzapfen Ø 12,4 (Bohrung Ø 12,64, kleben), vorn eine Vertiefung Ø 12,7 × 1,08 für
              den Bund von A, außen Ø 14,8 wie der Schaft.
Beide Magnete sind eingedruckt: Tasche Ø 3,3 × 2,16 unter einer Haut von 0,24 (2 Schichten bei 0,12), Pause vor
der ersten Schicht über der Tasche. Beide Teile stehend, Magnetseite oben, Höhen auf 0,12 gerastert.
Aufruf: python3 magnetadapter.py  -> out/stecknase_adapter_kappe_pla.*, out/stecknase_adapter_schaft_pla.*
"""
import os
import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
LH = 0.12
R_ZAPFEN = 6.2            # wie der Schaftzapfen (TPU-Bohrung Ø 12,0)
L_HUELSE = 12.0           # Tiefe der Bohrung in der TPU-Hülse
UEBERSTAND = 1.0          # Bund vor der Hülse
R_MAG, H_MAG = 1.65, 18 * LH      # Tasche Ø 3,3 × 2,16 für Magnet 3 × 2 (mit --zwei: 36 × LH = 4,32 für zwei hintereinander)
HAUT = 2 * LH             # 0,24 über dem Magnet
R_AUSSEN_B = 7.4          # wie der Schaft über dem Zapfen
R_MUFFE = R_ZAPFEN + 0.12 # Schaftzapfen Ø 12,4 in Ø 12,64 (kleben)
L_MUFFE = 11.7            # Zapfenlänge unter dem Schaftkegel
R_VERT = R_ZAPFEN + 0.15  # Vertiefung für den Bund von A
T_VERT = 9 * LH           # 1,08 (Bund 1,0 + Luft)


def revolve(pts):
    return cq.Workplane('XZ').polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def zyl(r, z0, z1):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(0, 0, z0))


def adapter_kappe():
    h = L_HUELSE + UEBERSTAND                               # 13,0
    s = revolve([(0, 0), (R_ZAPFEN - 0.5, 0), (R_ZAPFEN, 0.5), (R_ZAPFEN, h - 0.3), (R_ZAPFEN - 0.3, h), (0, h)])
    s = s.cut(zyl(3.5, -0.1, h - HAUT - H_MAG - 0.8))        # Gewicht sparen (unten offen, in der TPU-Hülse)
    z1 = h - HAUT
    s = s.cut(zyl(R_MAG, z1 - H_MAG, z1))
    return s, z1


def adapter_schaft():
    z_t1 = L_MUFFE + 0.6                                     # Boden über der Muffe
    z_m0 = round((z_t1) / LH) * LH
    z_m1 = z_m0 + H_MAG
    z_v = z_m1 + HAUT                                        # Boden der Vertiefung
    h = z_v + T_VERT
    s = revolve([(0, 0), (R_AUSSEN_B - 0.4, 0), (R_AUSSEN_B, 0.4), (R_AUSSEN_B, h - 0.4), (R_AUSSEN_B - 0.4, h), (0, h)])
    s = s.cut(zyl(R_MUFFE, -0.1, L_MUFFE))
    s = s.cut(cq.Solid.makeCone(R_MUFFE + 0.4, R_MUFFE, 0.4, cq.Vector(0, 0, -0.01)))   # Einführfase
    s = s.cut(zyl(R_MAG, z_m0, z_m1))
    s = s.cut(zyl(R_VERT, z_v, h + 0.1))
    s = s.cut(cq.Solid.makeCone(R_VERT, R_VERT + 0.3, 0.3, cq.Vector(0, 0, h - 0.3)))   # Kante der Vertiefung brechen
    return s, z_m1, h


if __name__ == '__main__':
    import sys
    suf = ''
    if '--zwei' in sys.argv:                                 # zwei Magnete hintereinander je Seite
        H_MAG = 36 * LH
        suf = '_2mag'
    os.makedirs(OUT, exist_ok=True)
    a, pa = adapter_kappe()
    b, pb, hb = adapter_schaft()
    for nm, s in (('stecknase_adapter_kappe_pla' + suf, a), ('stecknase_adapter_schaft_pla' + suf, b)):
        assert s.isValid() and len(s.Solids()) == 1, nm
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, nm + '.stl'), tolerance=0.01, angularTolerance=0.1)
        cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, nm + '.step'))
        bb = s.BoundingBox()
        print(f'{nm}: Ø {bb.xlen:.2f} × {bb.zlen:.2f} mm, {s.Volume() / 1000 * 1.24:.2f} g PLA')
    print(f'Pause Kappenadapter: Tasche endet bei {pa:.2f} mm (Pause vor der Schicht bis {pa + LH:.2f})')
    print(f'Pause Schaftadapter: Tasche endet bei {pb:.2f} mm (Pause vor der Schicht bis {pb + LH:.2f}); Höhe {hb:.2f}')
