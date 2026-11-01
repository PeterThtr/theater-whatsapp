#!/usr/bin/env python3
"""Anprobe-Schale (Nasenkappe mit Auflagefläche) aus einem Scaniverse-STL.

Eingabe: STL des Nasenscans (Einheit Meter, wird nach mm umgerechnet).
Koordinaten nach dem Zentrieren: X seitlich, Y oben, Z aus dem Gesicht heraus (Nasenspitze bei Z ~ +22).
Die Schale wird als Fläche entlang der geglätteten Flächennormalen verdickt:
  innen  = Scanfläche + SPIEL (Klebefilm)
  aussen = innen + t(v), t wird zum Rand hin dünner (auslaufende Klebekante).

Aufruf: python3 anprobe.py scan.stl --scale 1.0 --out out/
"""
import argparse, collections, os
import numpy as np
import trimesh
from matplotlib.path import Path
from scipy import sparse
from scipy.sparse.csgraph import connected_components, dijkstra

# ---- Umriss der Schale in der Vorderansicht (X, Y) in mm, unskaliert (Koordinaten des Scans)
# Auflagefläche rund um die Nase; Nasenlöcher werden unten über die Normalenregel freigelassen.
OUTLINE = [(-17, 31), (17, 31), (13, 24), (11.5, 16), (13, 9), (17, 3), (20, -4), (21, -12),
           (21, -20), (19, -26), (14, -29), (5, -30), (-5, -30), (-14, -29), (-19, -26),
           (-21, -20), (-21, -12), (-19, -4), (-16, 3), (-12.5, 9), (-11, 16), (-13, 24)]
UNTEN_Y = -12.0        # unterhalb davon werden nach unten zeigende Flächen entfernt ...
UNTEN_NY = -0.55       # ... wenn ihre Normale n_y kleiner ist (Unterseite der Spitze, Nasenlöcher)

SPIEL = 0.15           # Abstand Schale-Haut (Klebefilm)
T_WAND = 0.8           # Wandstärke
T_RAND = 0.4           # Wandstärke am äußersten Rand (eine Düsenbahn)
T_AUSLAUF = 6.0        # Länge, über die die Wand vom Rand aus dicker wird (mm)

# ---- Flügel mit Schlitz für ein flaches Gummiband (nur mit --fluegel)
BAND_B = 20.0          # Breite des Gummibands (mm), per --band einstellbar
FL_LAENGE = 34.0       # Länge des Flügels ab dem Schalenrand (mm)
FL_Y = -6.0            # Höhe der Flügelmitte (Y im Scan, unskaliert)
FL_DICKE = 1.6         # Dicke des Flügels
FL_UEBERLAPP = 4.0     # der Flügel beginnt so weit innerhalb der Schale (damit beide verschmelzen)
SCHLITZ_H = 3.5        # Schlitzhöhe in Bandrichtung (Band + Falte)
SCHLITZ_U = 20.0       # Abstand der Schlitzmitte vom Schalenrand
WANGE_STEIGUNG = -0.4  # mittlere Steigung der Wange seitlich der Nase (mm Z je mm X)
R_KOPF = 75.0          # angenommener Krümmungsradius der Kopfseite (Flügel biegen sich nach hinten)


def lade(pfad, skala):
    m = trimesh.load(pfad)
    m.apply_scale(1000.0)
    m.apply_translation(-m.bounds.mean(0))
    m.apply_scale(skala)
    return m


def waehle_flaechen(m, skala):
    c = m.triangles_center
    n = m.face_normals
    poly = Path(np.array(OUTLINE, float) * skala)
    sel = poly.contains_points(c[:, :2])
    # Unterseite der Spitze / Nasenlöcher: nur der größte zusammenhängende Bereich wird entfernt
    u = np.where(sel & (c[:, 1] < UNTEN_Y * skala) & (n[:, 1] < UNTEN_NY))[0]
    if len(u):
        adj = m.face_adjacency
        keep = np.isin(adj[:, 0], u) & np.isin(adj[:, 1], u)
        idx = {f: i for i, f in enumerate(u)}
        pairs = np.array([(idx[a], idx[b]) for a, b in adj[keep]]) if keep.any() else np.zeros((0, 2), int)
        comps = trimesh.graph.connected_components(pairs, nodes=np.arange(len(u)))
        gross = max(comps, key=len)
        sel[u[gross]] = False
    sub = m.submesh([np.where(sel)[0]], append=True)
    return bereinige(sub)


def bereinige(p):
    """Größte zusammenhängende Fläche; Pinch-Punkte am Rand und Dreiecke ohne zwei freie Nachbarn entfernen."""
    for _ in range(50):
        comps = trimesh.graph.connected_components(p.face_adjacency, nodes=np.arange(len(p.faces)))
        gross = max(comps, key=len)
        if len(gross) < len(p.faces):
            p = p.submesh([gross], append=True)
        F = np.asarray(p.faces)
        rand = randkanten(F)
        aus = collections.Counter(a for a, b in rand)
        pinch = {v for v, k in aus.items() if k > 1}
        if not pinch:
            return p
        rv = {a for a, b in rand} | {b for a, b in rand}
        bad = [i for i, f in enumerate(F) if pinch & set(f) and (set(f) & rv)]
        p = p.submesh([np.setdiff1d(np.arange(len(F)), bad)], append=True)
    return p


def glatte_normalen(p, iterationen=4):
    n = p.vertex_normals.copy()
    A = sparse.coo_matrix((np.ones(len(p.edges_unique)), (p.edges_unique[:, 0], p.edges_unique[:, 1])),
                          shape=(len(p.vertices),) * 2)
    A = (A + A.T).tocsr()
    for _ in range(iterationen):
        n = n + A @ n
        n /= np.linalg.norm(n, axis=1, keepdims=True)
    return n


def randkanten(faces):
    kanten = set()
    for f in faces:
        for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
            kanten.add((a, b))
    return [(a, b) for a, b in kanten if (b, a) not in kanten]


def verdicke(V, F, N, t, spiel=None):
    """Verdickt eine offene Fläche entlang N: innen = V + spiel*N, aussen = innen + t. Gibt einen geschlossenen Körper."""
    spiel = SPIEL if spiel is None else spiel
    nv = len(V)
    F = np.asarray(F)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    if (fn * N[F].mean(1)).sum() < 0:
        F = F[:, ::-1]
    rand = randkanten(F)
    V_in = V + spiel * N
    V_out = V + (spiel + t)[:, None] * N
    verts = np.vstack([V_out, V_in])
    wall = []
    for a, b in rand:
        wall.append((a, b + nv, b))        # a_out, b_in, b_out
        wall.append((a, a + nv, b + nv))   # a_out, a_in, b_in
    faces = np.vstack([F, F[:, ::-1] + nv, np.array(wall)])
    s = trimesh.Trimesh(verts, faces, process=True)
    if s.volume < 0:
        s.invert()
    return s


def baue_schale(p, skala):
    trimesh.smoothing.filter_taubin(p, lamb=0.5, nu=-0.53, iterations=12)
    V = np.asarray(p.vertices); F = np.asarray(p.faces); nv = len(V)
    N = glatte_normalen(p)
    rand = randkanten(F)
    rv = np.array(sorted({a for a, b in rand}))
    # Abstand zum Rand entlang der Fläche
    E = p.edges_unique
    w = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    G = sparse.coo_matrix((w, (E[:, 0], E[:, 1])), shape=(nv, nv)); G = (G + G.T).tocsr()
    d = dijkstra(G, indices=rv, min_only=True)
    t = T_RAND + (T_WAND - T_RAND) * np.clip(d / (T_AUSLAUF * skala), 0, 1)
    s = verdicke(V, F, N, t)
    return s, d, t, (V, F, N, rv)


def baue_fluegel(V, N, rv, seite, skala, band_b, t_wand=None, fl_dicke=None):
    """Flügel als 2,5D-Fläche über dem Umriss (X, Y): innen die Scanfläche, außen eine gerundete Fortsetzung
    (Steigung am Schalenrand, nach hinten zunehmend gekrümmt wie die Wange, Radius R_KOPF).
    Der Umriss hat einen Schlitz für das Gummiband. Wird um die Schale herum verschmolzen."""
    from shapely.geometry import box, Polygon, LineString, Point
    from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
    t_wand = T_WAND if t_wand is None else t_wand
    fl_dicke = FL_DICKE if fl_dicke is None else fl_dicke
    H = band_b + 7.0
    L = FL_LAENGE * skala
    yc = FL_Y * skala
    foot = Polygon(np.array(OUTLINE, float) * skala)
    lin = LinearNDInterpolator(V[:, :2], V[:, 2]); nea = NearestNDInterpolator(V[:, :2], V[:, 2])

    def f_scan(x, y):
        z = lin(x, y)
        return np.where(np.isnan(z), nea(x, y), z)

    cache = {}

    def xb(y):
        k = round(float(y) * 4) / 4
        if k not in cache:
            seg = LineString([(0, k), (seite * 200, k)]).intersection(foot)
            cache[k] = abs(seg.bounds[0] if seite < 0 else seg.bounds[2]) if not seg.is_empty else 15.0 * skala
        return cache[k]

    # Randwerte entlang Y vorab bestimmen und glätten (der Scanrand ist unruhig, das soll nicht in den Flügel wandern)
    from scipy.ndimage import gaussian_filter1d
    yg = np.arange(yc - H / 2 - 6, yc + H / 2 + 6.01, 0.5)
    x0g = np.array([xb(v) - 1.5 for v in yg])
    fbg = np.array([float(f_scan(seite * x0, v)) for x0, v in zip(x0g, yg)])
    f2g = np.array([float(f_scan(seite * (x0 - 3.0), v)) for x0, v in zip(x0g, yg)])
    slg = np.clip((fbg - f2g) / 3.0, -1.6, 0.5)
    sig = 3.0 / 0.5
    x0g, fbg, slg = (gaussian_filter1d(q, sig, mode='nearest') for q in (x0g, fbg, slg))

    def f(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        xx, yy = np.broadcast_arrays(x, y)
        a = np.abs(xx)
        x0 = np.interp(yy, yg, x0g)
        xi = np.maximum(a - x0, 0.0)
        fb = np.interp(yy, yg, fbg); sl = np.interp(yy, yg, slg)
        ext = fb + WANGE_STEIGUNG * xi + (sl - WANGE_STEIGUNG) * 6.0 * (1 - np.exp(-xi / 6.0)) - 0.5 * xi * xi / R_KOPF
        inside = np.where(a <= x0, f_scan(xx, yy), ext)
        return inside

    x_in = xb(yc + H / 2) - 6 * skala
    x_out = xb(yc) + L
    r = 7.0 * skala
    ur = box(0, yc - H / 2, x_out, yc + H / 2)
    ur = ur.buffer(-r).buffer(r).union(box(0, yc - H / 2, x_in + 8, yc + H / 2))
    ur = ur.intersection(box(x_in, yc - H / 2, x_out, yc + H / 2))
    xs = xb(yc) + SCHLITZ_U * skala
    sl_h, sl_b = SCHLITZ_H, band_b + 1.0
    schlitz = box(xs - sl_h / 2, yc - sl_b / 2, xs + sl_h / 2, yc + sl_b / 2).buffer(-1.2).buffer(1.2)
    poly = ur.difference(schlitz)
    if seite < 0:
        from shapely import affinity
        poly = affinity.scale(poly, xfact=-1, yfact=1, origin=(0, 0))
    v2, f2 = trimesh.creation.triangulate_polygon(poly, triangle_args='pq28a2.0', engine='triangle')
    x, y = v2[:, 0], v2[:, 1]
    z = f(x, y)
    h = 0.4
    gx = (f(x + h, y) - f(x - h, y)) / (2 * h); gy = (f(x, y + h) - f(x, y - h)) / (2 * h)
    N3 = np.stack([-gx, -gy, np.ones_like(gx)], 1); N3 /= np.linalg.norm(N3, axis=1, keepdims=True)
    V3 = np.stack([x, y, z], 1)
    d = np.array([foot.exterior.distance(Point(px, py)) if not foot.contains(Point(px, py)) else 0.0 for px, py in zip(x, y)])
    t = t_wand + (fl_dicke - t_wand) * np.clip(d / (8.0 * skala), 0, 1)
    return verdicke(V3, f2, N3, t)


def druckrichtung(s):
    """Dreht um die X-Achse; wählt die Lage mit der kleinsten Überhangfläche (Neigung < 30° zur Waagrechten)."""
    best = None
    for ang in range(0, 360, 15):
        T = trimesh.transformations.rotation_matrix(np.radians(ang), [1, 0, 0])
        r = s.copy(); r.apply_transform(T)
        n = r.face_normals; z = r.triangles_center[:, 2]
        flach = (n[:, 2] < -np.cos(np.radians(30))) & (z > r.bounds[0, 2] + 0.3)
        a = r.area_faces[flach].sum()
        basis = r.area_faces[(n[:, 2] < -0.99) & (z <= r.bounds[0, 2] + 0.3)].sum()
        score = a - 0.05 * basis
        if best is None or score < best[0]:
            best = (score, ang, a, basis)
    T = trimesh.transformations.rotation_matrix(np.radians(best[1]), [1, 0, 0])
    r = s.copy(); r.apply_transform(T)
    r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]])
    return r, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scan'); ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--out', default='out')
    ap.add_argument('--fluegel', action='store_true', help='Flügel mit Schlitz für Gummiband ergänzen')
    ap.add_argument('--band', type=float, default=BAND_B, help='Breite des Gummibands in mm')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    m = lade(a.scan, a.scale)
    p = waehle_flaechen(m, a.scale)
    s, d, t, (V, F, N, rv) = baue_schale(p, a.scale)
    name = 'anprobe_schale'
    teile = [s]
    if a.fluegel:
        name = 'anprobe_fluegel'
        for seite in (+1, -1):
            f = baue_fluegel(V, N, rv, seite, a.scale, a.band)
            print(f"Flügel {seite:+d}: wasserdicht={f.is_watertight}, Volumen={f.volume / 1000:.2f} cm³, Ausdehnung={np.round(f.extents, 1)}")
            teile.append(f)
        s = trimesh.boolean.union(teile, engine='manifold')
    tag = f"{int(round(a.scale * 100)):03d}"
    print(f"Maßstab {a.scale}: wasserdicht={s.is_watertight}, Volumen={s.volume / 1000:.2f} cm³, "
          f"Fläche Schale={p.area / 100:.1f} cm², Ausdehnung={np.round(s.extents, 1)}, Körper={len(s.split(only_watertight=False))}")
    s.export(os.path.join(a.out, f"{name}_{tag}_lage_scan.stl"))
    r, best = druckrichtung(s)
    print(f"Druckrichtung: Drehung um X {best[1]}°, Überhangfläche {best[2]:.0f} mm², Basisfläche {best[3]:.0f} mm²")
    r.export(os.path.join(a.out, f"{name}_{tag}.stl"))


if __name__ == '__main__':
    main()
