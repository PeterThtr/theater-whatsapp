#!/usr/bin/env python3
"""Kurze Nase ohne Schaft (18.11.): nur eine Halbkugel auf der TPU-Kappe (Steckhülse Ø 17,2, Bohrung Ø 12,0 × 12).

Zwei Varianten, beide PLA, Halbkugel R 8,6 = Außen-R der TPU-Hülse (geht bündig in die Hülse über):
  steck: Zapfen Ø 12,4 × 12 (wie der Schaftzapfen, 0,4 Pressung im TPU), darüber 45°-Kegel auf Ø 17,2, Halbkugel.
         Druck: Zapfen unten, Halbkugel oben, keine Stützen.
  4mag:  Gegenstück zum Kappenadapter …_kappe_pla_4mag (Bund 3 mm): Hülse Ø 17,2 mit Vertiefung Ø 12,7 × 3,12 unten,
         4 Magnettaschen Ø 3,3 × 2,04 im Boden der Vertiefung (Polung wie beim Schaftadapter), darüber Halbkugel.
         Druck: Vertiefung unten auf der Platte (Decke Ø 12,7 ist eine Brücke), Halbkugel oben.
Aufruf: python3 knolle.py -> out/stecknase_knolle_steck_pla.*, out/stecknase_knolle_pla_4mag.*
"""
import os
import cadquery as cq
import magnetadapter as M

R_K = 8.6


def halbkugel(z0):
    return cq.Solid.makeSphere(R_K, cq.Vector(0, 0, z0), angleDegrees1=0, angleDegrees2=90)


def knolle_steck():
    r = M.R_ZAPFEN
    zk = M.L_HUELSE                                  # 12: Oberkante der TPU-Hülse
    z1 = zk + (R_K - r)                              # 45°-Kegel bis Ø 17,2
    s = M.revolve([(0, 0), (r - 0.5, 0), (r, 0.5), (r, zk), (R_K, z1), (0, z1)])
    return s.fuse(halbkugel(z1)).clean()


def knolle_4mag():
    z_v = M.T_VERT4                                  # 3,12 Vertiefung (Bund 3,0 + 0,12)
    z_top = z_v + M.T_MAG4 + 0.8                     # Material über den Taschen
    r_v = M.R_ZAPFEN + M.LUFT4
    s = M.revolve([(r_v + 0.4, 0), (R_K - 0.3, 0), (R_K, 0.3), (R_K, z_top), (0, z_top), (0, z_v), (r_v, z_v), (r_v, 0.4)])
    s = s.fuse(halbkugel(z_top)).clean()
    # Taschen nach oben in die Decke der Vertiefung (taschen() schneidet von z_oben nach unten -> gespiegelt bauen)
    import math
    for k in range(4):
        a = math.pi / 2 * k
        x, y = M.R_Q * math.cos(a), M.R_Q * math.sin(a)
        s = s.cut(cq.Solid.makeCylinder(M.R_MAG4, M.T_MAG4 + 0.1, cq.Vector(x, y, z_v - 0.1)))
    return s


if __name__ == '__main__':
    os.makedirs(M.OUT, exist_ok=True)
    for nm, s in (('stecknase_knolle_steck_pla', knolle_steck()), ('stecknase_knolle_pla_4mag', knolle_4mag())):
        assert s.isValid() and len(s.Solids()) == 1, nm
        cq.exporters.export(cq.Workplane().add(s), os.path.join(M.OUT, nm + '.stl'), tolerance=0.01, angularTolerance=0.1)
        cq.exporters.export(cq.Workplane().add(s), os.path.join(M.OUT, nm + '.step'))
        bb = s.BoundingBox()
        print(f'{nm}: Ø {bb.xlen:.2f} × {bb.zlen:.2f} mm, {s.Volume() / 1000 * 1.24:.2f} g PLA (100 %)')
