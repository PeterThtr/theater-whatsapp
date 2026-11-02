#!/usr/bin/env python3
"""Holzstruktur auf der Außenfläche (Relief, damit die Prothese wie geschnitzt aussieht).

Die Fläche wird mit Manifold fein unterteilt (keine Risse) und dann entlang der Flächennormalen verschoben.
Verschoben wird nur die Außenseite (Normale zeigt nicht zur Haut). Die Hohlräume (Nase, Bohrung, Tasche, Kanal,
Bandschlitz) werden danach exakt abgezogen, bleiben also passgenau.

Das Relief besteht aus:
  - Jahresringen (Stammachse parallel zur Nasenachse Z, leicht gewellt: ergibt Fladern wie bei gesägtem Holz),
  - feinen Längsfasern,
  - zwei, drei Ästen (konzentrische Ringe um einen Punkt, in Faserrichtung gestreckt),
  - weichen Schnitzdellen mit großem Abstand (wie vom Schnitzeisen).
Maximale Tiefe etwa ±0,3 mm bei tiefe = 1.
"""
import numpy as np
import trimesh
import manifold3d as mf

# Äste: (x, y, z, Radius, Amplitude) im Koordinatensystem des Scans (X seitlich, Y oben, Z aus dem Gesicht heraus)
ASTE = [(4.0, -6.5, 62.0, 4.5, 0.30), (-9.0, -26.0, 78.0, 3.5, 0.26), (-32.0, -12.0, -25.0, 4.0, 0.26), (13.5, -14.0, 34.0, 3.2, 0.22)]


def _rauschen(P, skala, seed):
    """Weiche Rauschfunktion aus einigen Sinuswellen mit zufälligen Richtungen (kein Gitter, keine Kanten)."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(P))
    for _ in range(6):
        d = rng.normal(size=3); d /= np.linalg.norm(d)
        out += np.sin(2 * np.pi * (P @ d) / (skala * rng.uniform(0.7, 1.4)) + rng.uniform(0, 2 * np.pi))
    return out / 6.0


def hoehe(P, tiefe=1.0):
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    # Jahresringe: Stammachse parallel Z, seitlich unter dem Teil; Welligkeit entlang Z macht die Fladern
    x0, y0 = 28.0, -78.0
    wx = 2.8 * np.sin(z / 31.0 + 0.6) + 1.1 * np.sin(z / 11.5 + 1.3)
    wy = 1.8 * np.sin(z / 24.0 + 2.0)
    r = np.hypot(x - x0 + wx, y - y0 + wy) + 0.018 * z
    f = r / 3.1
    f = f - np.floor(f)
    ring = (np.sin(2 * np.pi * f) + 0.45 * np.sin(4 * np.pi * f + 0.7)) / 1.45
    h = 0.20 * ring
    # feine Längsfasern (quer fein, entlang Z lang)
    q = np.c_[x / 1.3, y / 1.3, z / 20.0]
    h += 0.05 * _rauschen(q, 1.0, 11) * 2.0
    # Äste
    for kx, ky, kz, R, A in ASTE:
        d = np.sqrt((x - kx) ** 2 + (y - ky) ** 2 + ((z - kz) * 0.5) ** 2)
        h += A * np.cos(2 * np.pi * d / 2.3) * np.exp(-(d / R) ** 2)
    # Schnitzdellen
    h += 0.14 * _rauschen(P, 17.0, 23)
    return np.clip(h * tiefe, -0.3 * max(tiefe, 1.0), 0.3 * max(tiefe, 1.0))


def holzstruktur(mesh, tiefe=1.0, kante=0.9):
    """Gibt ein Trimesh mit Holzrelief auf der Außenseite zurück. kante = größte Kantenlänge nach dem Unterteilen (mm)."""
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32), tri_verts=np.asarray(mesh.faces, np.uint32)))
    M = M.refine_to_length(kante)
    mm = M.to_mesh()
    V = np.asarray(mm.vert_properties)[:, :3].astype(float)
    F = np.asarray(mm.tri_verts)
    t = trimesh.Trimesh(V, F, process=False)
    N = t.vertex_normals
    # Gewicht: Flächen, die zur Haut zeigen (Normale mit negativem Z), bleiben glatt; weicher Übergang
    w = np.clip((N[:, 2] + 0.45) / 0.35, 0.0, 1.0)
    w = w * w * (3 - 2 * w)
    d = hoehe(V, tiefe) * w
    V2 = V + N * d[:, None]
    M2 = mf.Manifold(mf.Mesh(vert_properties=V2.astype(np.float32), tri_verts=F.astype(np.uint32)))
    if M2.is_empty():
        raise RuntimeError('Holzstruktur: Manifold leer (Tiefe zu groß?)')
    mm2 = M2.to_mesh()
    return trimesh.Trimesh(np.asarray(mm2.vert_properties)[:, :3], np.asarray(mm2.tri_verts), process=False)


# ---------------------------------------------------------------------------------------------------------------
# Stil „grob“: grob geschnitztes Holz mit Astlöchern (2.11.)
#   - Schnitzfacetten: Mulden wie vom Hohleisen, in Faserrichtung (Z) gestreckt, mit scharfen Graten dazwischen.
#     Sie liegen ganz AUSSERHALB der glatten Fläche (Grate bis +A, Muldengrund 0): die Wand wird nirgends dünner.
#   - Maserung: Jahresringe wie oben, gröber (4 mm), die Ringe weichen um die Äste aus.
#   - Astlöcher: Vertiefung mit rundem Grund, darum ein erhabener Astring und ein paar konzentrische Ringe.
#     Die Tiefe wird an jeder Stelle auf (Wanddicke − WAND_MIN) begrenzt; die Wanddicke wird mit einem Strahl nach
#     innen am fertigen Körper (mit allen Hohlräumen) gemessen.

WAND_MIN = 0.8          # so viel Wand bleibt unter einem Astloch mindestens stehen


def _facetten(V, saat, A, streck):
    """Mulden um Saatpunkte: h = A·(2·d1/(d1+d2))², d1/d2 = Abstand zum nächsten / zweitnächsten Saatpunkt
    (in Faserrichtung gestaucht gemessen). Mitte der Mulde 0, Grat zwischen zwei Mulden A."""
    from scipy.spatial import cKDTree
    s = np.array([1.0, 1.0, 1.0 / streck])
    d, i = cKDTree(saat * s).query(V * s, k=2)
    g = 2 * d[:, 0] / np.maximum(d[:, 0] + d[:, 1], 1e-9)
    rng = np.random.default_rng(5)
    a = A * rng.uniform(0.6, 1.15, len(saat))[i[:, 0]]       # nicht jede Mulde gleich tief
    return a * g * g


def hoehe_grob(V, aeste, tiefe=1.0, saat=None):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    # Ast-Abstände (in Faserrichtung gestreckt: Äste sind oval)
    dk = [np.sqrt((x - p[0]) ** 2 + (y - p[1]) ** 2 + ((z - p[2]) * 0.6) ** 2) for p, r, o in aeste]
    # Jahresringe, Stammachse parallel Z; um jeden Ast schieben sich die Ringe auseinander
    x0, y0 = 30.0, -80.0
    wx = 3.2 * np.sin(z / 29.0 + 0.6) + 1.3 * np.sin(z / 10.5 + 1.3)
    wy = 2.0 * np.sin(z / 23.0 + 2.0)
    r = np.hypot(x - x0 + wx, y - y0 + wy) + 0.02 * z
    for d, (p, rl, offen) in zip(dk, aeste):
        r = r + 2.2 * rl * np.exp(-(d / (2.6 * rl)) ** 2)
    f = r / 4.0
    f = f - np.floor(f)
    ring = 0.5 + 0.5 * (np.sin(2 * np.pi * f) + 0.45 * np.sin(4 * np.pi * f + 0.7)) / 1.45   # 0..1
    h = 0.20 * ring
    # Fasern
    q = np.c_[x / 1.1, y / 1.1, z / 18.0]
    h += 0.05 * (1 + _rauschen(q, 1.0, 11))
    # Schnitzfacetten
    if saat is not None:
        h += _facetten(V, saat, 0.55, 2.2)
    # Äste: Loch, Astring, konzentrische Ringe
    for d, (p, rl, offen) in zip(dk, aeste):
        # offen: Astloch (Vertiefung); sonst geschlossener Ast (leicht gewölbter Kern, nur auf dünnen Stellen)
        loch = (-2.2 if offen else 0.15) * np.clip(1 - (d / rl) ** 2, 0, None) ** 0.6
        rand = 0.40 * np.exp(-((d - rl * 1.15) / (0.35 * rl)) ** 2)
        ringe = 0.12 * (1 + np.cos(2 * np.pi * (d - rl) / 1.6)) * np.exp(-((d - rl) / (1.6 * rl)) ** 2) * (d > rl)
        um = np.exp(-(d / (1.8 * rl)) ** 4)                   # um den Ast herum ist die Fläche glatter (Ast wurde umschnitzt)
        h = h * (1 - 0.6 * um) + loch + rand + ringe
    return h * tiefe


def wanddicke(koerper, P, N, max_d=6.0):
    """Wanddicke an den Punkten P: Strahl von P (knapp innen) nach −N bis zur nächsten Fläche des Körpers."""
    origins = P - N * 0.02
    t = np.full(len(P), max_d)
    loc, idx_ray, _ = koerper.ray.intersects_location(origins, -N, multiple_hits=True)
    if len(loc):
        dist = np.linalg.norm(loc - origins[idx_ray], axis=1)
        ok = dist > 0.05
        np.minimum.at(t, idx_ray[ok], dist[ok])
    return t


def holzstruktur_grob(mesh, koerper, aeste, tiefe=1.0, kante=0.8, facette=7.0):
    """Grob geschnitztes Holz. mesh = Außenkörper (ohne Hohlräume), koerper = fertiger Körper mit Hohlräumen
    (für die Wanddicke unter den Astlöchern). aeste = [((x, y, z) Zielpunkt, Lochradius), ...]; die Punkte werden
    auf die nächste nach außen zeigende Stelle der Fläche gezogen. Ein drittes Element False macht einen geschlossenen
    Ast ohne Loch (für dünne Stellen wie die Flügel).
    Rückgabe: (Trimesh, Liste der tatsächlichen Astpunkte mit Lochradius und erreichter Tiefe)."""
    M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32), tri_verts=np.asarray(mesh.faces, np.uint32)))
    M = M.refine_to_length(kante)
    mm = M.to_mesh()
    V = np.asarray(mm.vert_properties)[:, :3].astype(float)
    F = np.asarray(mm.tri_verts)
    t = trimesh.Trimesh(V, F, process=False)
    N = t.vertex_normals
    w = np.clip((N[:, 2] + 0.45) / 0.35, 0.0, 1.0)
    w = w * w * (3 - 2 * w)
    # Astpunkte auf die Fläche ziehen (nur nach außen zeigende Stellen)
    aussen = np.where(w > 0.95)[0]
    from scipy.spatial import cKDTree
    kd = cKDTree(V[aussen])
    aeste = [a if len(a) == 3 else (a[0], a[1], True) for a in aeste]
    aeste_ist = [(V[aussen[kd.query(np.asarray(p, float))[1]]], rl, o) for p, rl, o in aeste]
    # Saatpunkte der Facetten: gleichmäßig auf der Fläche verteilt
    saat, _ = trimesh.sample.sample_surface_even(t, 4000, radius=facette * 0.5, seed=3)
    d = hoehe_grob(V, aeste_ist, tiefe, saat) * w
    # Astlöcher: Tiefe auf Wanddicke − WAND_MIN begrenzen
    neg = np.where(d < -0.05)[0]
    tiefe_ist = []
    if len(neg):
        # Wanddicke in zwei Richtungen messen (Punktnormale und gemittelte Normale der Umgebung des Astes),
        # der kleinere Wert zählt: an den schrägen Lochflanken zeigt die Punktnormale sonst zur Seite
        dick = wanddicke(koerper, V[neg], N[neg])
        A_f = t.area_faces; Fn = t.face_normals; C = t.triangles_center
        for p, rl, o in aeste_ist:
            dd = np.linalg.norm(C - p, axis=1)
            um = (dd > 1.6 * rl) & (dd < 3.5 * rl)
            nm = (Fn[um] * A_f[um, None]).sum(0); nm /= np.linalg.norm(nm)
            nah = np.linalg.norm(V[neg] - p, axis=1) < 1.5 * rl
            if nah.any():
                d2 = wanddicke(koerper, V[neg][nah], np.tile(nm, (nah.sum(), 1)))
                dick[nah] = np.minimum(dick[nah], d2)
        d[neg] = np.maximum(d[neg], -(dick - WAND_MIN))
    for p, rl, o in aeste_ist:
        nah = np.linalg.norm(V - p, axis=1) < rl
        tiefe_ist.append(float(-d[nah].min()) if (nah.any() and o) else 0.0)
    V2 = V + N * d[:, None]
    M2 = mf.Manifold(mf.Mesh(vert_properties=V2.astype(np.float32), tri_verts=F.astype(np.uint32)))
    if M2.is_empty():
        raise RuntimeError('Holzstruktur grob: Manifold leer (Fläche schneidet sich, Tiefe zu groß?)')
    mm2 = M2.to_mesh()
    out = trimesh.Trimesh(np.asarray(mm2.vert_properties)[:, :3], np.asarray(mm2.tri_verts), process=False)
    return out, [(p, rl, ti) for (p, rl, o), ti in zip(aeste_ist, tiefe_ist)]
