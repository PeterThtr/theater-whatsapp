#!/usr/bin/env python3
"""TPU-Nasenprothese mit Hülse um Segment 1, Lappen-Flügeln mit Schlitz für Gummiband und Fußtasche.

Baut auf anprobe.py auf (Scan -> Schale + Flügel). Koordinaten wie dort: X seitlich, Y oben, Z aus dem Gesicht heraus.
Die Teleskopachse liegt waagerecht (parallel Z) auf Höhe YA (Nasenspitze).

Bauteile (alles TPU, ein Körper):
  Schale + Flügel   Haut-Auflage; Flügel als runde Lappen über den Wangenknochen mit Schlitz für ein flaches Band
  Keil (Hülle)      konvexe Hülle von Nasenspitze und Hülse, minus Nase (Haut + SPIEL)
  Hülse             Außen-Ø 32,4, umschließt Segment 1 (Bohrung 27,1: Presssitz)
  Fußtasche         nimmt den runden Fuß (Platte + Becher, Ø 29,8) auf, Schulter hält ihn
  Kanal             Ø 3,9 für den 4-mm-Schlauch, vom Fuß in einem Bogen nach unten (oder seitlich) hinaus
Alle Außenflächen werden vor dem Abziehen der Hohlräume organisch verrundet (Schließen mit Radius R_FILET).

Aufruf: python3 prothese.py scan.stl --out out/ [--band 20] [--austritt unten|links|rechts]
                                      [--z-platte 38] [--kanal-radius 14] [--filet 5]
"""
import argparse, os, sys
import numpy as np
import trimesh
from shapely.geometry import Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anprobe as A

# ---- Teleskop-Maße (aus code/nase/tele.py)
SEG1_R = 13.8          # Außenradius Segment 1
FUSS_R = 14.9          # Außenradius Fußbecher
FUSS_PLATTE = 1.5
FUSS_BECHER = 4.0

# ---- Prothese
YA = -19.0             # Höhe der Teleskopachse (Nasenspitze)
Z_PLATTE = 38.0        # Rückseite der Fußplatte (Z); die Nasenspitze liegt bei Z ~ 22,5
HUELSE_LAENGE = 45.0   # Hülse um Segment 1 (ab Segmentanfang)
HUELSE_R = 16.2        # Außenradius der Hülse
BOHRUNG_R = SEG1_R - 0.25   # Presssitz, 0,5 mm Übermaß im Durchmesser
TASCHE_R = FUSS_R + 0.2
KANAL_D = 3.9          # für 4-mm-PTFE-Schlauch (leicht untermaßig, TPU hält ihn)
KANAL_BOGEN = 14.0     # Biegeradius des Kanals (der Schlauch muss das mitmachen: vorher testen!)
R_FILET = 5.0          # Verrundungsradius der Übergänge (Schließen)
STUTZEN_R = 4.3        # Außenradius des Schlauchstutzens (Flansch), Wand um den 3,9-mm-Kanal etwa 2,3 mm
STUTZEN_L = 11.0       # Länge des Stutzens über dem Austritt des Kanals
STUTZEN_EINBETT = 6.0  # so weit reicht der Stutzen in den Körper hinein

# TPU-Wandstärken
T_WAND, T_RAND, FL_DICKE = 1.2, 0.5, 2.0
KEIL_Z_AB = 6.0        # Ab dieser Z-Höhe beginnt der Keil (Nasenspitzenbereich)
KEIL_Y_BIS = 2.0
NASEN_UMRISS = [(-19.5, 33), (19.5, 33), (19.5, -35), (-19.5, -35)]   # Bereich des Scans, aus dem der Nasenkörper entsteht


def kanal_pfad(richtung, z0, radius=None, n=40):
    """Mittellinie des Schlauchkanals: von der Fußrückseite zunächst nach hinten, dann im Bogen weg."""
    R = KANAL_BOGEN if radius is None else radius
    # seitlich muss der Bogen etwas weiter laufen (die Hülle ist dort rund und am Rand der Nase etwa 16 mm von der Achse)
    th = np.radians(np.linspace(0, 85 if richtung == 'unten' else 105, n))
    z = z0 - R * np.sin(th)
    d = R - R * np.cos(th)                 # seitliche Auslenkung
    if richtung == 'unten':
        pts = np.stack([np.zeros_like(z), YA - d, z], 1)
        tang = np.array([0.0, -np.sin(th[-1]), -np.cos(th[-1])])
    else:
        sgn = 1.0 if richtung == 'rechts' else -1.0
        pts = np.stack([sgn * d, np.full_like(z, YA), z], 1)
        tang = np.array([sgn * np.sin(th[-1]), 0.0, -np.cos(th[-1])])
    tang /= np.linalg.norm(tang)
    ext = pts[-1] + np.outer(np.linspace(1, 40, 20), tang)
    start = np.array([[pts[0][0], pts[0][1], z0 + 1.5]])
    return np.vstack([start, pts, ext])


def stutzen(punkt, tang, laenge=STUTZEN_L, einbett=STUTZEN_EINBETT, r=STUTZEN_R):
    """Kurzer Schlauchstutzen: Zylinder entlang der Kanal-Tangente, vorn mit gerundeter Kante."""
    h = einbett + laenge
    prof = np.array([[0, 0], [r, 0], [r, h - 1.2], [r - 1.2, h], [0, h]])
    m = trimesh.creation.revolve(prof, sections=64)
    m.apply_translation([0, 0, -einbett])
    T = trimesh.geometry.align_vectors([0, 0, 1], tang)
    m.apply_transform(T)
    m.apply_translation(punkt)
    return m


def spiegeln_x(m):
    r = m.copy()
    r.apply_transform(trimesh.transformations.reflection_matrix([0, 0, 0], [1, 0, 0]))
    if r.volume < 0:
        r.invert()
    return r


def zylinder(r, z0, z1, y=YA, x=0.0, sections=128):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=sections)
    c.apply_translation([x, y, (z0 + z1) / 2])
    return c


def verrunden(m, r, pitch=0.6, sigma=1.0, level=0.7):
    """Organische Übergänge: Voxel-Schließen mit Radius r füllt konkave Ecken mit Kehlen. Zurückgegeben wird ein
    glattes Netz, das knapp innerhalb der exakten Fläche liegt (level > 0,5) und nur in den Kehlen darüber
    hinausgeht. Es wird anschließend mit dem exakten Körper vereinigt."""
    from scipy import ndimage as ndi
    from skimage import measure
    vox = m.voxelized(pitch).fill()
    occ = np.asarray(vox.matrix).astype(bool)
    pad = int(np.ceil(r / pitch)) + 4
    occ = np.pad(occ, pad)
    rv = r / pitch
    dil = ndi.distance_transform_edt(~occ) <= rv
    clos = (ndi.distance_transform_edt(dil) > rv) | occ
    fld = ndi.gaussian_filter(clos.astype(np.float32), sigma)
    v, f, _, _ = measure.marching_cubes(fld, level)
    v = v - pad
    world = trimesh.transformations.transform_points(v, vox.transform)
    out = trimesh.Trimesh(world, f)
    trimesh.repair.fix_normals(out)
    return out


def baue(scan, skala, band, austritt, z_platte=None, kanal_radius=None, filet=None, stutzen_spiegel=True):
    z_platte = Z_PLATTE if z_platte is None else z_platte
    kanal_radius = KANAL_BOGEN if kanal_radius is None else kanal_radius
    filet = R_FILET if filet is None else filet
    A.T_WAND, A.T_RAND, A.FL_DICKE = T_WAND, T_RAND, FL_DICKE
    m = A.lade(scan, skala)
    p = A.waehle_flaechen(m, skala)
    schale, d, t, (V, F, N, rv) = A.baue_schale(p, skala)
    teile = [schale]; fraeser = []
    for seite in (+1, -1):
        w, fr = A.baue_fluegel(V, N, rv, seite, skala, band, t_wand=T_WAND, fl_dicke=FL_DICKE, schlitz_im_koerper=False)
        teile.append(w); fraeser.append(fr)
    # Keil: konvexe Hülle von Spitzenbereich der Schale und dem Hülsenanfang
    sv = schale.vertices
    E = sv[(sv[:, 2] >= KEIL_Z_AB) & (sv[:, 1] <= KEIL_Y_BIS)]
    z_start = z_platte + 9.0
    th = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    ring = np.stack([HUELSE_R * np.cos(th), YA + HUELSE_R * np.sin(th), np.full_like(th, z_start)], 1)
    keil = trimesh.convex.convex_hull(np.vstack([E, ring]))
    # Hülse mit gerundeter Vorderkante
    z_seg0 = z_platte + FUSS_PLATTE
    z_ende = z_seg0 + HUELSE_LAENGE
    prof = np.array([[0, z_start - 1], [HUELSE_R, z_start - 1], [HUELSE_R, z_ende - 1.5], [HUELSE_R - 1.5, z_ende], [0, z_ende]])
    huelse = trimesh.creation.revolve(prof, sections=128)
    huelse.apply_translation([0, YA, 0])
    teile += [keil, huelse]
    pfad = kanal_pfad(austritt, z_platte, kanal_radius)
    if austritt in ('links', 'rechts') and stutzen_spiegel is not None:
        pe = pfad[40]                                   # Ende des Bogens (n = 40 Punkte, Index 0 ist der Start)
        tg = pfad[40] - pfad[39]; tg /= np.linalg.norm(tg)
        st = stutzen(pe, tg)
        teile.append(st)
        if stutzen_spiegel:                             # Gegenstutzen auf der anderen Seite (ohne Bohrung): Symmetrie
            teile.append(spiegeln_x(st))
    ausen = trimesh.boolean.union(teile, engine='manifold')
    if filet > 0:
        weich = verrunden(ausen, filet)
        ausen = trimesh.boolean.union([ausen, weich], engine='manifold')
    # Nase (Haut + Spiel) nach hinten verlängert, Tasche, Bohrung, Kanal, Bandschlitze: werden abgezogen
    # Der Nasenkörper (alles hinter der Haut, inklusive Unterseite der Spitze und Nasenlöcher) wird als Prisma
    # entlang -Z aus der vollständigen Scanfläche erzeugt. Die Fläche ist (fast) ein Höhenfeld über (X, Y).
    pv = A.waehle_flaechen(m, skala, outline=NASEN_UMRISS, unten_frei=False)
    trimesh.smoothing.filter_taubin(pv, lamb=0.5, nu=-0.53, iterations=12)
    Vv = np.asarray(pv.vertices); Nv = A.glatte_normalen(pv)
    Vf = Vv + A.SPIEL * Nv
    nase = A.verdicke(Vf, np.asarray(pv.faces), np.tile([0.0, 0.0, -1.0], (len(Vf), 1)), np.full(len(Vf), 60.0), spiel=0.0)
    z_tasche0 = z_platte - 0.2
    z_tasche1 = z_seg0 + FUSS_BECHER + 0.2
    tasche = zylinder(TASCHE_R, z_tasche0, z_tasche1)
    bohrung = zylinder(BOHRUNG_R, z_tasche1 - 0.5, z_ende + 2)
    kanal = trimesh.creation.sweep_polygon(Point(0, 0).buffer(KANAL_D / 2, 16), pfad)
    cut = trimesh.boolean.union([nase, tasche, bohrung, kanal] + fraeser, engine='manifold')
    tpu = trimesh.boolean.difference([ausen, cut], engine='manifold')
    return tpu


def hauptkoerper(s):
    """Boolesche Operationen hinterlassen winzige Splitter und fast flächenlose Dreiecke, die beim STL-Export
    (float32) zu Löchern werden. Darum: größten Körper nehmen, durch Manifold schicken und dort mit kleiner
    Toleranz vereinfachen (verschmilzt Splitter, bleibt ein gültiger Körper). Geprüft wird nach einem echten
    STL-Hin-und-Rück-Lauf, das ist die strengere Prüfung als die im Speicher."""
    import io
    import manifold3d as mf
    m0 = max(s.split(only_watertight=False), key=lambda p: abs(p.volume))
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(m0.vertices, np.float32), tri_verts=np.asarray(m0.faces, np.uint32)))
    if M.is_empty():
        return m0
    best = None
    for tol in (0.001, 0.01, 0.0005, 0.002, 0.02):
        mm = M.simplify(tol).to_mesh()
        r = trimesh.Trimesh(np.asarray(mm.vert_properties)[:, :3], np.asarray(mm.tri_verts))
        b = io.BytesIO(); r.export(b, file_type='stl'); b.seek(0)
        q = trimesh.load(b, file_type='stl')
        if q.is_watertight and len(q.split(only_watertight=False)) == 1:
            return r
        best = best or r
    return best


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
    ap.add_argument('--z-platte', type=float, default=Z_PLATTE, help='Z der Fußplatten-Rückseite (Nasenspitze: 22,5)')
    ap.add_argument('--kanal-radius', type=float, default=KANAL_BOGEN)
    ap.add_argument('--filet', type=float, default=R_FILET, help='Verrundungsradius der Übergänge, 0 = aus')
    ap.add_argument('--stutzen', choices=['aus', 'einseitig', 'symmetrisch'], default='symmetrisch',
                    help='Schlauchstutzen am seitlichen Austritt; symmetrisch = Gegenstutzen ohne Bohrung auf der anderen Seite')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sp = {'aus': None, 'einseitig': False, 'symmetrisch': True}[a.stutzen]
    tpu = hauptkoerper(baue(a.scan, a.scale, a.band, a.austritt, a.z_platte, a.kanal_radius, a.filet, sp))
    print(f"TPU-Prothese: wasserdicht={tpu.is_watertight}, Volumen={tpu.volume / 1000:.1f} cm³ "
          f"(~{tpu.volume / 1000 * 1.21:.0f} g bei 100 %), Ausdehnung={np.round(tpu.extents, 1)}, Flächen={len(tpu.faces)}")
    r, ueber = lage_huelse_oben(tpu)
    print(f"Lage Hülse oben: Höhe {r.extents[2]:.0f} mm, Überhangfläche (Neigung < 30°) {ueber:.0f} mm²")
    tpu.export(os.path.join(a.out, 'prothese_tpu_lage_scan.stl'))
    r.export(os.path.join(a.out, 'prothese_tpu.stl'))


if __name__ == '__main__':
    main()
