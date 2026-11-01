#!/usr/bin/env python3
"""TPU-Nasenprothese mit Hülse um Segment 1, Flügeln mit Schlitz für Gummiband und Fußtasche.

Baut auf anprobe.py auf (Scan -> Schale + Flügel). Koordinaten wie dort: X seitlich, Y oben, Z aus dem Gesicht heraus.
Die Teleskopachse liegt waagerecht (parallel Z) auf Höhe YA (Nasenspitze).

Bauteile (alles TPU, ein Körper):
  Schale + Flügel   Haut-Auflage, Flügel mit Schlitz für ein flaches Gummiband
  Keil (Hülle)      konvexe Hülle von Nasenspitze und Hülse, minus Nase (Haut + SPIEL)
  Hülse             Außen-Ø 32,4, umschließt Segment 1 (Bohrung 27,1: Presssitz)
  Fußtasche         nimmt den runden Fuß (Platte + Becher, Ø 29,8) auf, Schulter hält ihn
  Kanal             Ø 3,9 für den 4-mm-Schlauch, vom Fuß in einem Bogen nach unten (oder seitlich) hinaus

Aufruf: python3 prothese.py scan.stl --out out/ [--band 20] [--austritt unten|links|rechts]
"""
import argparse, os, sys
import numpy as np
import trimesh
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anprobe as A

# ---- Teleskop-Maße (aus code/nase/tele.py)
SEG1_R = 13.8          # Außenradius Segment 1
SEG1_L = 63.5
FUSS_R = 14.9          # Außenradius Fußbecher
FUSS_PLATTE = 1.5
FUSS_BECHER = 4.0

# ---- Prothese
YA = -19.0             # Höhe der Teleskopachse (Nasenspitze)
Z_PLATTE = 46.0        # Rückseite der Fußplatte (Z, vor der Nasenspitze bei Z ~ 22,5)
HUELSE_LAENGE = 45.0   # Hülse um Segment 1 (ab Segmentanfang)
HUELSE_R = 16.2        # Außenradius der Hülse
BOHRUNG_R = SEG1_R - 0.25   # Presssitz, 0,5 mm Übermaß im Durchmesser
TASCHE_R = FUSS_R + 0.2
KANAL_D = 3.9          # für 4-mm-PTFE-Schlauch (leicht untermaßig, TPU hält ihn)
KANAL_BOGEN = 20.0     # Biegeradius des Kanals

# TPU-Wandstärken
T_WAND, T_RAND, FL_DICKE = 1.2, 0.5, 2.0
KEIL_Z_AB = 6.0        # Ab dieser Z-Höhe beginnt der Keil (Nasenspitzenbereich)
KEIL_Y_BIS = 2.0


def kanal_pfad(richtung, z0, n=40):
    """Mittellinie des Schlauchkanals: von der Fußrückseite zunächst nach hinten, dann im Bogen weg."""
    th = np.radians(np.linspace(0, 85, n))
    R = KANAL_BOGEN
    z = z0 - R * np.sin(th)
    d = R - R * np.cos(th)                 # seitliche Auslenkung
    if richtung == 'unten':
        pts = np.stack([np.zeros_like(z), YA - d, z], 1)
        tang = np.array([0, -np.sin(th[-1]), -np.cos(th[-1])]) if False else np.array([0, -np.sin(th[-1]), -np.cos(th[-1])])
        # Tangente am Ende: dz/dth = -R cos(th), dd/dth = R sin(th)
        tang = np.array([0.0, -np.sin(th[-1]), -np.cos(th[-1])])
    else:
        sgn = 1.0 if richtung == 'rechts' else -1.0
        pts = np.stack([sgn * d, np.full_like(z, YA), z], 1)
        tang = np.array([sgn * np.sin(th[-1]), 0.0, -np.cos(th[-1])])
    tang /= np.linalg.norm(tang)
    ext = pts[-1] + np.outer(np.linspace(1, 40, 20), tang)
    start = np.array([[pts[0][0], pts[0][1], z0 + 1.5]])
    return np.vstack([start, pts, ext])


def zylinder(r, z0, z1, y=YA, x=0.0, sections=128):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    c.apply_translation([x, y, (z0 + z1) / 2])
    return c


def baue(scan, skala, band, austritt):
    A.T_WAND, A.T_RAND, A.FL_DICKE = T_WAND, T_RAND, FL_DICKE
    m = A.lade(scan, skala)
    p = A.waehle_flaechen(m, skala)
    schale, d, t, (V, F, N, rv) = A.baue_schale(p, skala)
    teile = [schale]
    for seite in (+1, -1):
        teile.append(A.baue_fluegel(V, N, rv, seite, skala, band, t_wand=T_WAND, fl_dicke=FL_DICKE))
    # Keil: konvexe Hülle von Spitzenbereich der Schale und dem Hülsenanfang
    sv = schale.vertices
    E = sv[(sv[:, 2] >= KEIL_Z_AB) & (sv[:, 1] <= KEIL_Y_BIS)]
    z_start = Z_PLATTE + 9.0
    th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    ring = np.stack([HUELSE_R * np.cos(th), YA + HUELSE_R * np.sin(th), np.full_like(th, z_start)], 1)
    keil = trimesh.convex.convex_hull(np.vstack([E, ring]))
    # Hülse mit gerundeter Vorderkante
    z_seg0 = Z_PLATTE + FUSS_PLATTE
    z_ende = z_seg0 + HUELSE_LAENGE
    prof = np.array([[0, z_start - 1], [HUELSE_R, z_start - 1], [HUELSE_R, z_ende - 1.2], [HUELSE_R - 1.2, z_ende], [0, z_ende]])
    huelse = trimesh.creation.revolve(prof, sections=128)
    huelse.apply_translation([0, YA, 0])
    teile += [keil, huelse]
    ausen = trimesh.boolean.union(teile, engine='manifold')
    # Nase (Haut + Spiel) nach hinten verlängert: wird abgezogen
    Vf = V + A.SPIEL * N
    nase = A.verdicke(Vf, F, np.tile([0.0, 0.0, -1.0], (len(Vf), 1)), np.full(len(Vf), 60.0), spiel=0.0)
    # Tasche, Bohrung, Kanal
    z_tasche0 = Z_PLATTE - 0.2
    z_tasche1 = z_seg0 + FUSS_BECHER + 0.2
    tasche = zylinder(TASCHE_R, z_tasche0, z_tasche1)
    bohrung = zylinder(BOHRUNG_R, z_tasche1 - 0.5, z_ende + 2)
    pfad = kanal_pfad(austritt, Z_PLATTE)
    kreis = Point(0, 0).buffer(KANAL_D / 2, 16)
    kanal = trimesh.creation.sweep_polygon(kreis, pfad)
    cut = trimesh.boolean.union([nase, tasche, bohrung, kanal], engine='manifold')
    tpu = trimesh.boolean.difference([ausen, cut], engine='manifold')
    return tpu, dict(schale=schale, nase=nase, ausen=ausen, kanal=kanal)


def druckrichtung(s, schritt=15):
    """Sucht die Lage (Drehung um X und Y) mit der kleinsten Überhangfläche (Neigung unter 30° zur Waagrechten)."""
    n0 = s.face_normals; a = s.area_faces; c0 = s.triangles_center
    best = None
    for ax in range(0, 360, schritt):
        for ay in range(0, 180, schritt):
            R = trimesh.transformations.euler_matrix(np.radians(ax), np.radians(ay), 0, 'sxyz')[:3, :3]
            n = n0 @ R.T; z = (c0 @ R.T)[:, 2]
            zmin = (s.vertices @ R.T)[:, 2].min()
            flach = (n[:, 2] < -np.cos(np.radians(30))) & (z > zmin + 0.4)
            auf = (n[:, 2] < -0.98) & (z < zmin + 0.4)
            score = a[flach].sum() - 0.2 * a[auf].sum()
            if best is None or score < best[0]:
                best = (score, ax, ay, a[flach].sum(), a[auf].sum())
    R = trimesh.transformations.euler_matrix(np.radians(best[1]), np.radians(best[2]), 0, 'sxyz')
    r = s.copy(); r.apply_transform(R)
    r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]])
    return r, best


def hauptkoerper(s):
    """Boolesche Operationen hinterlassen winzige Splitter und flächenlose Dreiecke, die beim STL-Export
    (float32) zu Löchern werden. Darum: größten Körper nehmen, Koordinaten auf 0,001 mm runden und einmal
    durch Manifold schicken, das nur gültige, geschlossene Körper liefert."""
    import manifold3d as mf
    m = max(s.split(only_watertight=False), key=lambda p: abs(p.volume))
    m.vertices = np.round(m.vertices, 3)
    m.merge_vertices()
    m.update_faces(m.area_faces > 0)
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    mm = M.to_mesh()
    r = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts))
    return max(r.split(only_watertight=False), key=lambda p: abs(p.volume))


def lage_huelse_oben(s):
    """Druckfertige Lage: Hülse zeigt nach oben (Scan-Z = Druck-Z), Flügel zeigen nach unten."""
    r = s.copy()
    r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]])
    n = r.face_normals; z = r.triangles_center[:, 2]
    flach = (n[:, 2] < -np.cos(np.radians(30))) & (z > 0.4)
    return r, r.area_faces[flach].sum()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scan'); ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--out', default='out'); ap.add_argument('--band', type=float, default=20.0)
    ap.add_argument('--austritt', default='unten', choices=['unten', 'links', 'rechts'])
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tpu, dbg = baue(a.scan, a.scale, a.band, a.austritt)
    tpu = hauptkoerper(tpu)
    print(f"TPU-Prothese: wasserdicht={tpu.is_watertight}, Volumen={tpu.volume / 1000:.1f} cm³ "
          f"(~{tpu.volume / 1000 * 1.21:.0f} g bei 100 %), Ausdehnung={np.round(tpu.extents, 1)}")
    r, ueber = lage_huelse_oben(tpu)
    print(f"Lage Hülse oben: Höhe {r.extents[2]:.0f} mm, Überhangfläche (Neigung < 30°) {ueber:.0f} mm²")
    tpu.export(os.path.join(a.out, 'prothese_tpu_lage_scan.stl'))
    r.export(os.path.join(a.out, 'prothese_tpu.stl'))


if __name__ == '__main__':
    main()
