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
