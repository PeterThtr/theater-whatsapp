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

if '--draht' in sys.argv:
    os.environ['TELE_PROFIL'] = 'draht'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'nase'))
import anprobe as A
import tele as T

# ---- Teleskop-Maße (aus code/nase/tele.py, Profil Feder oder Draht)
SEG1_R = T.RO[1]       # Außenradius Segment 1
FUSS_R = T.CUP_RO      # Außenradius Fußbecher
FUSS_PLATTE = T.PLATE_T
FUSS_BECHER = T.CUP_H

# ---- Prothese
YA = -19.0             # Höhe der Teleskopachse (Nasenspitze)
Z_PLATTE = 38.0        # Rückseite der Fußplatte (Z); die Nasenspitze liegt bei Z ~ 22,5
HUELSE_LAENGE = 45.0   # Hülse um Segment 1 (ab Segmentanfang)
HUELSE_R = max(SEG1_R + 2.4, FUSS_R + 1.8) if T.DRAHT else 16.2   # Außenradius der Hülse
BOHRUNG_R = SEG1_R - 0.25   # Presssitz, 0,5 mm Übermaß im Durchmesser
TASCHE_R = FUSS_R + 0.2
KANAL_D = 3.9          # für 4-mm-PTFE-Schlauch (leicht untermaßig, TPU hält ihn)
KANAL_D_LANG = 4.15    # Kanal-Ø bei langem Kanal im Flügel (Schlauch gleitet, Stutzen/Kleber hält ihn)
KANAL_BOGEN = 14.0     # Biegeradius des Kanals (der Schlauch muss das mitmachen: vorher testen!)
R_FILET = 5.0          # Verrundungsradius der Übergänge (Schließen)
STUTZEN_R = 4.3        # Außenradius des Schlauchstutzens (Flansch), Wand um den 3,9-mm-Kanal etwa 2,3 mm
STUTZEN_L = 11.0       # Länge des Stutzens über dem Austritt des Kanals
STUTZEN_EINBETT = 6.0  # so weit reicht der Stutzen in den Körper hinein
BOSS_R = 4.1           # Außenradius des Schlauchwulstes entlang der Flügel (Wand um den 3,9-mm-Kanal etwa 2,1 mm)
BOSS_H = 2.0           # Mitte des Kanals über der Außenfläche des Flügels (Flügeldicke 2,0 → Kanalmitte 4,15 über der Haut)

# TPU-Wandstärken
T_WAND, T_RAND, FL_DICKE = 1.2, 0.5, 2.0
KEIL_Z_AB = 6.0        # Ab dieser Z-Höhe beginnt der Keil (Nasenspitzenbereich)
KEIL_Y_BIS = 2.0
# Umriss der Schale: oben bei Y 14 statt 31 (weniger Material an der Nasenwurzel), unten bleibt die Unterseite vor Z 15 erhalten
OUTLINE_P = [(-9.5, 14), (9.5, 14), (13, 9), (17, 3), (20, -4), (21, -12), (21, -20), (19, -26), (14, -29), (5, -30), (-5, -30),
             (-14, -29), (-19, -26), (-21, -20), (-21, -12), (-19, -4), (-16, 3), (-12.5, 9)]
UNTEN_Z_P = 15.0
NASEN_UMRISS = [(-19.5, 33), (19.5, 33), (19.5, -35), (-19.5, -35)]   # Bereich des Scans, aus dem der Nasenkörper entsteht


# ---- Andere Nase: Peters Scan wird in X, Y, Z linear verzerrt (Option --nase)
# Bezugswerte von Peters Nase: Messschieber 51,0 (Nasenwurzel–Spitze) und 33,9 (Nasenflügel), Projektion aus dem Scan:
# Nasenflügelansatz (Furche Nasenflügel/Wange, X ±18, Y −22, Z −10) bis Spitze (Y −19,4, Z 22,5) in der Seitenansicht 32,6.
# Im Scan: Nasenwurzel (tiefster Punkt) Y 24,4 / Z −6,7, Strecke zur Spitze 52,7 (dY 43,8, dZ 29,2).
REF_WURZEL_SPITZE, REF_PROJEKTION, REF_BREITE = 51.0, 32.6, 33.9
REF_SCAN_WURZEL_SPITZE, REF_SCAN_DY, REF_SCAN_DZ = 52.7, 43.8, 29.2


def morph_faktoren(wurzel_spitze, projektion, breite):
    """Faktoren (sx, sy, sz) für Peters Scan: Breite -> X, Projektion -> Z, Nasenwurzel–Spitze -> Y (mit dem schon
    verzerrten Z, damit die schräge Strecke stimmt). Die Messwerte werden wie Peters Messschieberwerte behandelt."""
    sx = breite / REF_BREITE
    sz = projektion / REF_PROJEKTION
    l_scan = wurzel_spitze * REF_SCAN_WURZEL_SPITZE / REF_WURZEL_SPITZE
    dy = np.sqrt(max(l_scan ** 2 - (REF_SCAN_DZ * sz) ** 2, 1.0))
    return sx, dy / REF_SCAN_DY, sz


def morph_konstanten(sx, sy, sz):
    """Alle festen Koordinaten (Umriss, Höhen), die sich auf Peters Scan beziehen, mitverzerren."""
    global OUTLINE_P, NASEN_UMRISS, UNTEN_Z_P, KEIL_Z_AB, KEIL_Y_BIS, YA
    A.MORPH = (sx, sy, sz)
    OUTLINE_P = [(x * sx, y * sy) for x, y in OUTLINE_P]
    NASEN_UMRISS = [(x * sx, y * sy) for x, y in NASEN_UMRISS]
    UNTEN_Z_P *= sz; KEIL_Z_AB *= sz; KEIL_Y_BIS *= sy; YA *= sy


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


def kanal_pfad_spitz(scan, z0, richtung, radius=None, psi_end=25.0, d_min=3.9, ds=0.5):
    """Seitlicher Kanal, der erst um die Nasenspitze herum nach außen und dann in einem spitzen Winkel nach
    hinten zur Wange läuft (S-Kurve aus zwei Bögen mit Radius R). psi_end ist der Winkel des Stutzens zur
    -Z-Achse (0 = genau nach hinten, 90 = quer). Der erste Bogen wird so weit gedreht, dass der Kanal überall
    mindestens d_min von der Haut entfernt bleibt (Kanalradius 1,95 + Spiel 0,15 + Wand 1,8).
    Rückgabe: (Pfad Start..Ende des zweiten Bogens, Tangente am Ende, Kanalpunkte für den Fräser)"""
    R = KANAL_BOGEN if radius is None else radius
    sgn = -1.0 if richtung == 'links' else 1.0

    def bauen(psi1):
        pts = [np.array([0.0, YA, z0 + 1.5])]
        p = np.array([0.0, z0])                       # (X, Z)
        psi = 0.0; pts.append(np.array([p[0], YA, p[1]]))
        step = ds / R
        # Bogen 1: Drehung nach außen bis psi1
        while psi < np.radians(psi1) - 1e-9:
            h = np.array([sgn * np.sin(psi), -np.cos(psi)])
            p = p + h * ds; psi += step; pts.append(np.array([p[0], YA, p[1]]))
        # Bogen 2: zurückdrehen bis psi_end
        while psi > np.radians(psi_end) + 1e-9:
            h = np.array([sgn * np.sin(psi), -np.cos(psi)])
            p = p + h * ds; psi -= step; pts.append(np.array([p[0], YA, p[1]]))
        h = np.array([sgn * np.sin(psi), 0.0, -np.cos(psi)])
        return np.array(pts), h / np.linalg.norm(h)

    best = None
    for psi1 in np.arange(max(psi_end + 5, 40), 125, 2.0):
        pts, h = bauen(psi1)
        stub = pts[-1] + np.outer(np.linspace(0, STUTZEN_L, 12), h)      # der Stutzen darf auch nicht in die Nase ragen
        dist = trimesh.proximity.closest_point(scan, np.vstack([pts[2:], stub]))[1].min()
        if dist >= d_min:
            best = (psi1, pts, h, dist); break
    if best is None:
        raise RuntimeError('kein Kanalpfad mit genug Abstand zur Haut gefunden')
    psi1, pts, h, dist = best
    ext = pts[-1] + np.outer(np.linspace(1, 30, 15), h)
    return pts, h, np.vstack([pts, ext]), dict(psi1=psi1, dist=dist)


def kanal_pfad_gerade(scan, z0, richtung, radius, alpha, phi, d_min=4.0, ds=0.5, gerade=12.0):
    """Flacher Kanal für einen steifen Schubdraht: von der Fußplatte zuerst in der Achse nach hinten, dann EIN Bogen
    mit großem Radius (Draht 1,5 mm Federstahl lief im Test bei R 45 gut) seitlich bzw. schräg nach unten (alpha:
    0 = seitlich, 90 = nach unten) um phi Grad, danach ein gerades Stück. Der Kanal bleibt überall mindestens d_min
    von der Haut (nur dort geprüft, wo der Scan die Haut kennt)."""
    sgn = -1.0 if richtung == 'links' else 1.0
    a = np.radians(alpha)
    u = np.array([sgn * np.cos(a), -np.sin(a), 0.0])
    ph = np.arange(0.0, np.radians(phi) + 1e-9, ds / radius)
    P = np.array([0.0, YA, z0]) + np.outer(radius * (1 - np.cos(ph)), u) + np.outer(-radius * np.sin(ph), [0.0, 0.0, 1.0])
    tg = np.sin(ph[-1]) * u - np.cos(ph[-1]) * np.array([0.0, 0.0, 1.0])
    Q = P[-1] + np.outer(np.arange(ds, gerade + 1e-9, ds), tg)
    pts = np.vstack([[[0.0, YA, z0 + 1.5]], P, Q])
    xmax = np.abs(scan.vertices[:, 0]).max() - 1.0
    d = trimesh.proximity.closest_point(scan, pts[1:])[1]
    inn = np.abs(pts[1:, 0]) < xmax
    dmin = float(d[inn].min()) if inn.any() else 99.0
    if dmin < d_min:
        raise RuntimeError('Kanal zu nah an der Haut')
    ext = pts[-1] + np.outer(np.linspace(1, 30, 15), tg)
    return pts, tg, np.vstack([pts, ext]), dict(psi1=float(phi), dist=dmin, radius=float(radius))


def kanal_pfad_fluegel(scan, z0, richtung, radius, psi_end, ctx, d_min=3.9, ds=0.5):
    """Schlauchkanal, der um die Nasenspitze läuft und dann im Flügel bis zum äußeren Rand weiterläuft
    (Wulst auf der Außenfläche des Flügels, unter dem Schlitz hindurch). Der Schlauch tritt erst am Flügelende aus.
    Aufbau: S-Kurve um die Spitze (zwei Bögen, Radius R), gerade nach hinten zur Wange, dann ein glatter Spline
    über die Außenfläche des Flügels bis kurz vor den äußeren Rand.
    Rückgabe wie kanal_pfad_spitz: (Pfad, Tangente am Ende, Pfad mit Verlängerung für den Fräser, Info)."""
    from scipy.interpolate import splprep, splev
    R = KANAL_BOGEN if radius is None else radius
    sgn = -1.0 if richtung == 'links' else 1.0
    f = ctx['f']
    O, ax_, nv_ = ctx['O'], ctx['a'], ctx['n']
    lm, Aa, Bb = ctx['lm'], ctx['A'], ctx['B']

    def flaechenpunkt(xa, y, hoehe):
        """Punkt in der Höhe `hoehe` über der Flügelfläche (entlang der Normalen), so verschoben, dass seine
        Projektion nach (X, Y) genau bei (sgn*xa, y) liegt (die Normale versetzt den Punkt sonst seitlich)."""
        h = 0.4
        ziel = np.array([sgn * xa, y]); c = ziel.copy()
        for _ in range(4):
            ca = abs(c[0])
            z = float(f(ca, c[1]))
            fx = (float(f(ca + h, c[1])) - float(f(ca - h, c[1]))) / (2 * h)
            fy = (float(f(ca, c[1] + h)) - float(f(ca, c[1] - h))) / (2 * h)
            n = np.array([-fx * sgn, -fy, 1.0]); n /= np.linalg.norm(n)     # f ist über |x| definiert
            q = np.array([c[0], c[1], z]) + hoehe * n
            c = c + (ziel - q[:2])
        return q

    hc = A.SPIEL + FL_DICKE + BOSS_H                  # Kanalmitte über der Haut-Seite des Flügels
    vb = -(Bb - BOSS_R - 1.3)                         # Pfad läuft am unteren Rand des Lappens (lokales v)
    lokal = [(6.0, vb), (lm * 0.65, vb), (lm - 3.0, vb), (lm + 2.0, vb + 0.6), (lm + Aa - 4.5, vb + 4.0), (lm + Aa - 2.0, vb + 8.0)]
    steuer = [tuple(O + u * ax_ + v * nv_) for u, v in lokal]
    wing = np.array([flaechenpunkt(xa, y, hc) for xa, y in steuer])

    def s_kurve(psi1, psi_e):
        pts = [np.array([0.0, YA, z0 + 1.5])]
        p = np.array([0.0, z0]); psi = 0.0; pts.append(np.array([p[0], YA, p[1]])); step = ds / R
        while psi < np.radians(psi1) - 1e-9:
            hh = np.array([sgn * np.sin(psi), -np.cos(psi)]); p = p + hh * ds; psi += step
            pts.append(np.array([p[0], YA, p[1]]))
        while psi > np.radians(psi_e) + 1e-9:
            hh = np.array([sgn * np.sin(psi), -np.cos(psi)]); p = p + hh * ds; psi -= step
            pts.append(np.array([p[0], YA, p[1]]))
        return np.array(pts), np.array([sgn * np.sin(psi), 0.0, -np.cos(psi)])

    best = None; log = []
    for psi_e in (psi_end, psi_end + 7, psi_end + 14, psi_end + 22):
        for sfac in (0.15, 0.8):
            for psi1 in np.arange(max(psi_e + 5, 50), 125, 4.0):
                sk, h = s_kurve(psi1, psi_e)
                E = sk[-1]
                # gerader Abschnitt nach hinten, bis der Flügelanfang noch ca. 10 mm entfernt ist
                L = max((E[2] - wing[0][2] - 10.0) / max(-h[2], 0.2), 0.0)
                gerade = [E + k * h for k in np.arange(6.0, L + 1e-6, 6.0)]
                ctrl = np.vstack([sk[::8], [E]] + ([np.array(gerade)] if gerade else []) + [wing])
                keep = np.r_[True, np.linalg.norm(np.diff(ctrl, axis=0), axis=1) > 1.5]       # doppelte Punkte entfernen
                ctrl = ctrl[keep]
                u = np.r_[0, np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))]
                try:
                    tck, _ = splprep(ctrl.T, u=u, s=len(ctrl) * sfac, k=3)
                except Exception as e:
                    continue
                uu = np.arange(0, u[-1], ds)
                pts = np.array(splev(uu, tck)).T
                d1 = np.array(splev(uu, tck, der=1)).T; d2 = np.array(splev(uu, tck, der=2)).T
                kappa = np.linalg.norm(np.cross(d1, d2), axis=1) / np.maximum(np.linalg.norm(d1, axis=1) ** 3, 1e-9)
                rad = 1.0 / max(kappa[2:-2].max(), 1e-9)
                if rad < R - 1.0:
                    log.append((round(float(psi_e)), round(float(psi1)), sfac, '-', round(float(rad), 1)))
                    continue
                dist = trimesh.proximity.closest_point(scan, pts[2:])[1]
                mask = np.abs(pts[2:, 0]) < 19.0 * A.MORPH[0]               # nur dort, wo der Scan die Haut kennt
                dmin = dist[mask].min() if mask.any() else 99.0
                log.append((round(float(psi_e)), round(float(psi1)), sfac, round(float(dmin), 1), round(float(rad), 1)))
                if dmin >= d_min:
                    best = (psi1, pts, dmin, rad, psi_e); break
            if best: break
        if best: break
    if best is None:
        raise RuntimeError('kein Kanalpfad durch den Flügel mit genug Wand und Biegeradius gefunden; beste Versuche (psi_end, psi1, s, dmin, Radius): ' + str(sorted(log, key=lambda q: -q[4])[:4]))
    psi1, pts, dmin, rad, psi_e = best
    tg = pts[-1] - pts[-4]; tg /= np.linalg.norm(tg)
    ext = pts[-1] + np.outer(np.linspace(1, 30, 15), tg)
    return pts, tg, np.vstack([pts, ext]), dict(psi1=psi1, dist=dmin, radius=rad, psi_end_ist=psi_e)


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


def baue(scan, skala, band, austritt, z_platte=None, kanal_radius=None, filet=None, stutzen_spiegel=True, winkel=None,
         im_fluegel=False, holz=0.0, holz_stil='fein', gerade=None):
    z_platte = Z_PLATTE if z_platte is None else z_platte
    kanal_radius = KANAL_BOGEN if kanal_radius is None else kanal_radius
    filet = R_FILET if filet is None else filet
    A.T_WAND, A.T_RAND, A.FL_DICKE = T_WAND, T_RAND, FL_DICKE
    A.OUTLINE = OUTLINE_P
    A.UNTEN_Z = UNTEN_Z_P
    m = A.lade(scan, skala)
    p = A.waehle_flaechen(m, skala)
    schale, d, t, (V, F, N, rv) = A.baue_schale(p, skala)
    seite_k = {'links': -1, 'rechts': +1}.get(austritt)
    extra = None; fraeser = []; teile = [schale]
    info = {}; pfad_spitz = None; pfad = None
    # --- Flügelfläche kennenlernen (für den Kanalpfad im Flügel)
    ctx = None
    if seite_k is not None and (winkel is not None or im_fluegel):
        _, _, ctx = A.baue_fluegel(V, N, rv, seite_k, skala, band, t_wand=T_WAND, fl_dicke=FL_DICKE, schlitz_im_koerper=False)
    if seite_k is not None and gerade is not None:
        R_g, alpha_g, phi_g = gerade
        for zp in np.arange(z_platte, z_platte + 60.1, 0.5):
            try:
                pfad_spitz = kanal_pfad_gerade(m, zp, austritt, R_g, alpha_g, phi_g)
                z_platte = float(zp)
                break
            except RuntimeError:
                continue
        if pfad_spitz is None:
            raise RuntimeError('kein gerader Kanalpfad gefunden')
    elif seite_k is not None and winkel is not None:
        # Fußplatte so weit nach vorn schieben, wie der Kanal mit seiner Wand um die Nasenspitze herum braucht
        for zp in np.arange(z_platte, z_platte + 14.1, 0.5):
            try:
                if im_fluegel:
                    pfad_spitz = kanal_pfad_fluegel(m, zp, austritt, kanal_radius, winkel, ctx)
                else:
                    pfad_spitz = kanal_pfad_spitz(m, zp, austritt, kanal_radius, winkel)
                z_platte = float(zp)
                break
            except RuntimeError:
                continue
        if pfad_spitz is None:
            raise RuntimeError('kein Kanalpfad mit genug Wand gefunden, Winkel oder Radius ändern')
    # --- Zusatzfläche der Flügel unter dem Schlauchwulst
    if pfad_spitz is not None and im_fluegel:
        from shapely.geometry import LineString
        pts_w = pfad_spitz[0]
        sel = np.abs(pts_w[:, 0]) > 12.0
        xy = np.c_[np.abs(pts_w[sel, 0]), pts_w[sel, 1]]
        extra = LineString(xy).buffer(BOSS_R + 1.2, 24)
    for seite in (+1, -1):
        w, fr, _ = A.baue_fluegel(V, N, rv, seite, skala, band, t_wand=T_WAND, fl_dicke=FL_DICKE,
                                  schlitz_im_koerper=False, extra_poly=extra)
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
    if pfad_spitz is not None:
        pts, tg, pfad, info = pfad_spitz
        info['z_platte'] = z_platte
        r_boss = BOSS_R if im_fluegel else STUTZEN_R
        boss = trimesh.creation.sweep_polygon(Point(0, 0).buffer(r_boss, 24), pts[1:])
        st = stutzen(pts[-1], tg, laenge=STUTZEN_L - 3, einbett=4.0, r=r_boss)
        teile += [boss, st]
        if stutzen_spiegel:                             # Gegenstück auf der anderen Seite (ohne Bohrung): Symmetrie
            teile += [spiegeln_x(boss), spiegeln_x(st)]
    else:
        pfad = kanal_pfad(austritt, z_platte, kanal_radius)
        if austritt in ('links', 'rechts') and stutzen_spiegel is not None:
            pe = pfad[40]
            tg = pfad[40] - pfad[39]; tg /= np.linalg.norm(tg)
            st = stutzen(pe, tg)
            teile.append(st)
            if stutzen_spiegel:
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
    tasche = zylinder(TASCHE_R, z_tasche0, z_tasche1, y=YA)
    bohrung = zylinder(BOHRUNG_R, z_tasche1 - 0.5, z_ende + 2, y=YA)
    kd = KANAL_D_LANG if (im_fluegel or gerade is not None) else KANAL_D       # der lange Kanal im Flügel braucht Luft zum Einschieben
    kanal = trimesh.creation.sweep_polygon(Point(0, 0).buffer(kd / 2, 16), pfad)
    kanaele = [kanal]
    if stutzen_spiegel == 'beide':                       # zweiter Kanal spiegelgleich: der Schlauch kann links oder rechts laufen
        kanaele.append(spiegeln_x(kanal))
    cut = trimesh.boolean.union([nase, tasche, bohrung] + kanaele + fraeser, engine='manifold')
    if holz > 0:
        import holz as H                                # Holzrelief auf der Außenseite, danach werden die Hohlräume exakt abgezogen
        if holz_stil == 'grob':
            glatt = trimesh.boolean.difference([ausen, cut], engine='manifold')    # für die Wanddicke unter den Astlöchern
            z_spitze = float(m.vertices[:, 2].max())
            aeste = [((4.0, YA + HUELSE_R, z_seg0 + 20.0), 3.0),                  # Hülse oben
                     ((-0.7 * HUELSE_R, YA - 0.7 * HUELSE_R, z_ende - 11.0), 2.4),  # Hülse unten links
                     ((13.0, YA + 3.0, 0.5 * (z_spitze + z_start)), 2.6),       # Keil rechts
                     ((-30.0, YA + 4.0, -20.0), 2.0, False),                   # linker Flügel: geschlossener Ast (Flügel zu dünn für ein Loch)
                     ((34.0, YA + 6.0, -24.0), 1.6, False)]                    # rechter Flügel: geschlossener Ast
            ausen, info['aeste'] = H.holzstruktur_grob(ausen, glatt, aeste, tiefe=holz)
        else:
            ausen = H.holzstruktur(ausen, tiefe=holz)
    tpu = trimesh.boolean.difference([ausen, cut], engine='manifold')
    return tpu, info


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
    ap.add_argument('--out', default='out'); ap.add_argument('--draht', action='store_true', help='Maße des schlanken Drahtsatzes (TELE_PROFIL=draht)'); ap.add_argument('--band', type=float, default=12.0)
    ap.add_argument('--austritt', default='unten', choices=['unten', 'links', 'rechts'])
    ap.add_argument('--z-platte', type=float, default=Z_PLATTE, help='Z der Fußplatten-Rückseite (Nasenspitze: 22,5)')
    ap.add_argument('--kanal-radius', type=float, default=KANAL_BOGEN)
    ap.add_argument('--kanal-gerade', default=None, help='flacher Kanal für steifen Draht: "Radius,Richtung,Bogen" in mm/Grad, '
                    'z. B. 45,20,60 (Richtung 0 = seitlich, 90 = nach unten); mit --austritt links|rechts, ohne --winkel/--im-fluegel')
    ap.add_argument('--kanal-d', type=float, default=None, help='Durchmesser des Schlauchkanals im Flügel (Standard 4,15; TPU druckt Kanäle enger, 4,5 schont den Schlauch)')
    ap.add_argument('--filet', type=float, default=R_FILET, help='Verrundungsradius der Übergänge, 0 = aus')
    ap.add_argument('--stutzen', choices=['aus', 'einseitig', 'symmetrisch', 'beidseitig'], default='symmetrisch',
                    help='Schlauchstutzen am seitlichen Austritt; symmetrisch = Gegenstutzen ohne Bohrung auf der anderen Seite; beidseitig = auch der Gegenkanal ist gebohrt')
    ap.add_argument('--im-fluegel', action='store_true', help='Schlauchkanal läuft im Flügel bis zum äußeren Rand (nur mit --winkel und seitlichem Austritt)')
    ap.add_argument('--winkel', type=float, default=None, help='Stutzen-Winkel zur -Z-Achse in Grad bei seitlichem Austritt (z. B. 25 = spitz zur Wange); ohne Angabe: quer')
    ap.add_argument('--holz', type=float, default=0.0, help='Holzrelief auf der Außenseite (0 = aus, 1 = normal, 1,5 = kräftiger)')
    ap.add_argument('--holz-stil', choices=['fein', 'grob'], default='fein', help='fein = Maserung und weiche Dellen; grob = grob geschnitzt mit Facetten und Astlöchern')
    ap.add_argument('--wand', type=float, default=None, help='Wandstärke der Schale auf der Nase in mm (Standard 1,2; dünn: 0,8)')
    ap.add_argument('--fluegel-dicke', type=float, default=None, help='Dicke der Flügel in mm (Standard 2,0; dünn: 1,5)')
    ap.add_argument('--achse-y', type=float, default=None, help='Höhe der Teleskopachse (Standard −19 = Höhe der Nasenspitze); tiefer macht den Keil auf der Nase dünner')
    ap.add_argument('--nase', default=None, help='andere Nase: "Nasenwurzel–Spitze,Projektion,Breite" in mm (Messschieber), '
                    'z. B. 49.2,31.8,27.8; Projektion = Nasenflügelansatz bis Spitze in der Seitenansicht')
    ap.add_argument('--spiel', type=float, default=None, help='Abstand Schale–Haut in mm (Standard 0,15)')
    a = ap.parse_args()
    global T_WAND, T_RAND, FL_DICKE, YA, KANAL_D_LANG
    if a.kanal_d is not None:
        KANAL_D_LANG = a.kanal_d
    if a.nase:
        w, pj, b = (float(v) for v in a.nase.split(','))
        sx, sy, sz = morph_faktoren(w, pj, b)
        morph_konstanten(sx, sy, sz)
        print(f"Nase {w}/{pj}/{b} mm: Verzerrung des Scans X {sx:.3f}, Y {sy:.3f}, Z {sz:.3f}; Teleskopachse Y {YA:.1f}")
    if a.spiel is not None:
        A.SPIEL = a.spiel
    if a.achse_y is not None:
        YA = a.achse_y * (A.MORPH[1] if a.nase else 1.0)
    if a.wand is not None:
        T_WAND = a.wand; T_RAND = min(T_RAND, a.wand)
    if a.fluegel_dicke is not None:
        FL_DICKE = a.fluegel_dicke
    os.makedirs(a.out, exist_ok=True)
    sp = {'aus': None, 'einseitig': False, 'symmetrisch': True, 'beidseitig': 'beide'}[a.stutzen]
    roh, info = baue(a.scan, a.scale, a.band, a.austritt, a.z_platte, a.kanal_radius, a.filet, sp, a.winkel, a.im_fluegel, a.holz, a.holz_stil,
                    tuple(float(v) for v in a.kanal_gerade.split(',')) if a.kanal_gerade else None)
    for p, rl, ti in info.get('aeste', []):
        print(f"{'Astloch' if ti > 0 else 'Ast (geschlossen)'} bei X {p[0]:.1f} Y {p[1]:.1f} Z {p[2]:.1f}: Ø {2 * rl:.1f}" + (f", Tiefe {ti:.2f} mm" if ti > 0 else ''))
    if info.get('psi1') is not None: print(f"Kanal: erster Bogen {info['psi1']:.0f}°, Abstand Kanalmitte–Haut {info['dist']:.1f} mm, Fußplatte bei Z {info['z_platte']:.1f}" + (f", kleinster Radius {info['radius']:.1f} mm" if 'radius' in info else ''))
    tpu = hauptkoerper(roh)
    print(f"TPU-Prothese: wasserdicht={tpu.is_watertight}, Volumen={tpu.volume / 1000:.1f} cm³ "
          f"(~{tpu.volume / 1000 * 1.21:.0f} g bei 100 %), Ausdehnung={np.round(tpu.extents, 1)}, Flächen={len(tpu.faces)}")
    r, ueber = lage_huelse_oben(tpu)
    print(f"Lage Hülse oben: Höhe {r.extents[2]:.0f} mm, Überhangfläche (Neigung < 30°) {ueber:.0f} mm²")
    tpu.export(os.path.join(a.out, 'prothese_tpu_lage_scan.stl'))
    r.export(os.path.join(a.out, 'prothese_tpu.stl'))


if __name__ == '__main__':
    main()
