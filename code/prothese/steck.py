#!/usr/bin/env python3
"""Steck-Nase ohne Funktion (Pinocchio-Nase, Ende als plan aufsitzende Halbkugel), hält ohne Kleber und ohne Band.

Halt: TPU-Kappe auf der Nase mit leichter Pressung (Innenfläche 0,15 mm unter der Haut), sie greift über die
Nasenflügel (breiteste Stelle hinter der Spitze) und unter die Nasenspitze (vor den Nasenlöchern). Nasenlöcher
bleiben frei (Atmung). Grundlage: allgemeine Frauennase (Peters Scan verzerrt auf 49,2 / 31,8 / 27,8).

Längen L = Abstand Gesicht (Z = 0) bis Vorderkante der Puppennase:
  kurz : einteilig TPU, Halbkugel (flache Seite vorn auf der Kappe).
  200 / 400: TPU-Kappe mit Steckhülse + hohler PETG-Schaft (Wand 0,9) mit Puppennase am Ende; 400 in 3 Stücken
             (je < 170 mm hoch, passt auch auf den A1 Mini), Stöße gesteckt und geklebt.
Aufruf: python3 steck.py scan/nase_scaniverse_original_m.stl --out out/
"""
import argparse, os, sys
import numpy as np
import trimesh
sys.argv_save = list(sys.argv); sys.argv = [sys.argv[0], '--draht']
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prothese as P
sys.argv = sys.argv_save
A = P.A

NASE = (49.2, 31.8, 27.8)
SPIEL = -0.15                 # Pressung der Kappe
T_WAND, T_RAND = 1.4, 0.6     # Kappe, zum Rand dünner (legt sich an)
# Steckverbindung Kappe/Schaft
R_ZAPFEN = 6.2                # Zapfen am Schaft (Ø 12,4)
R_BOHR = 6.0                  # Bohrung in der TPU-Hülse (0,4 Übermaß im Ø)
L_ZAPFEN = 12.0
R_HUELSE = 8.6
# Schaft
R_SCHAFT0 = 7.4               # außen am Kappenende
R_SCHAFT1 = 4.5               # außen am Schaftende = Radius der End-Halbkugel
T_SCHAFT = 0.9
R_KURZ = 8.0                  # Halbkugel der kurzen Nase
STOSS_L = 10.0                # Steckzapfen an den Stößen des 400er-Schafts
H_MAX = 178.0               # A1 Mini: 180 mm Bauhöhe


def ellipsoid(c, ax, sub=4):
    e = trimesh.creation.icosphere(subdivisions=sub, radius=1.0)
    e.apply_scale(ax); e.apply_translation(c); return e


def halbkugel(z_flach, r, ya):
    """Halbkugel, flache Seite bei z_flach (quer zur Achse), Kuppe nach vorn (+Z)."""
    k = trimesh.creation.icosphere(subdivisions=5, radius=r)
    k.apply_translation([0, ya, z_flach])
    box = trimesh.creation.box(bounds=[[-r - 1, ya - r - 1, z_flach], [r + 1, ya + r + 1, z_flach + r + 1]])
    return trimesh.boolean.intersection([k, box], engine='manifold')


def kegelrohr(r0, r1, z0, z1, ya, n=96):
    pr = np.array([[0, z0], [r0, z0], [r1, z1], [0, z1]])
    m = trimesh.creation.revolve(pr, sections=n)
    m.apply_translation([0, ya, 0]); return m


def kappe_basis(scan):
    if not getattr(P, '_gemorpht', False):
        sx, sy, sz = P.morph_faktoren(*NASE); P.morph_konstanten(sx, sy, sz); P._gemorpht = True
    A.T_WAND, A.T_RAND, A.SPIEL = T_WAND, T_RAND, SPIEL
    A.OUTLINE = P.OUTLINE_P; A.UNTEN_Z = P.UNTEN_Z_P
    m = A.lade(scan, 1.0)
    p = A.waehle_flaechen(m, 1.0)
    schale, *_ = A.baue_schale(p, 1.0)
    pv = A.waehle_flaechen(m, 1.0, outline=P.NASEN_UMRISS, unten_frei=False)
    trimesh.smoothing.filter_taubin(pv, lamb=0.5, nu=-0.53, iterations=12)
    Vv = np.asarray(pv.vertices); Nv = A.glatte_normalen(pv)
    nase = A.verdicke(Vv + SPIEL * Nv, np.asarray(pv.faces), np.tile([0.0, 0.0, -1.0], (len(Vv), 1)), np.full(len(Vv), 60.0), spiel=0.0)
    z_tip = float(m.vertices[:, 2].max())
    return m, schale, nase, z_tip, P.YA


def kappe(scan, variante):
    m, schale, nase, z_tip, ya = kappe_basis(scan)
    teile = [schale]
    cut = [nase]
    info = {}
    if variante == 'kurz':
        zf = z_tip + T_WAND - 0.5                  # flache Seite knapp vor der Spitze (verschmilzt mit der Kappe)
        teile.append(halbkugel(zf, R_KURZ, ya))
        teile.append(kegelrohr(R_KURZ, R_KURZ, zf - 3.0, zf + 0.01, ya))   # kurzer Bund hinter der flachen Seite
        info['L'] = zf + R_KURZ
    else:
        z0 = z_tip + T_WAND + 0.6                  # Boden der Steckbohrung (vor der Kappe)
        teile.append(kegelrohr(R_HUELSE, R_HUELSE, z_tip - 6.0, z0 + L_ZAPFEN, ya))
        cut.append(kegelrohr(R_BOHR, R_BOHR, z0, z0 + L_ZAPFEN + 1, ya))
        info['z_bohr'] = z0
    aus = trimesh.boolean.union(teile, engine='manifold')
    aus = trimesh.boolean.union([aus, P.verrunden(aus, 4.0)], engine='manifold')
    k = trimesh.boolean.difference([aus] + cut, engine='manifold')
    teile_k = sorted(k.split(only_watertight=False), key=lambda q: -abs(q.volume))
    info['koerper'] = [round(abs(q.volume) / 1000, 2) for q in teile_k[:4]]
    return P.hauptkoerper(k), info, (z_tip, ya)


def schaft(L, z_bohr, ya):
    """Hohler Schaft vom Kappenende (Zapfen in der Bohrung) bis zur End-Halbkugel; L = Scheitel der Halbkugel."""
    z_hals = L - R_SCHAFT1                          # flache Seite der Halbkugel = Schaftende
    z_kap = z_bohr + L_ZAPFEN                       # Stirn der TPU-Hülse
    aussen = [kegelrohr(R_ZAPFEN, R_ZAPFEN, z_bohr + 0.3, z_kap + 0.5, ya),
              kegelrohr(R_ZAPFEN, R_SCHAFT0, z_kap - 0.01, z_kap + (R_SCHAFT0 - R_ZAPFEN), ya),   # 45°-Übergang (druckbar)
              kegelrohr(R_SCHAFT0, R_SCHAFT1, z_kap + (R_SCHAFT0 - R_ZAPFEN) - 0.01, z_hals + 0.01, ya),
              halbkugel(z_hals, R_SCHAFT1, ya)]
    s = trimesh.boolean.union(aussen, engine='manifold')
    # innen hohl: Zapfen und Schaft, oben mit 45°-Spitze geschlossen (unter der Halbkugel)
    ri0 = R_ZAPFEN - T_SCHAFT
    ri1 = R_SCHAFT1 - T_SCHAFT
    zi_end = z_hals - ri1
    # Innen parallel zum 45°-Übergang außen (sonst wird die Wand dort nur 0,2 dick -> leere Schichten im Slicer)
    dr = (R_SCHAFT0 - T_SCHAFT) - ri0
    z_i0 = z_kap + T_SCHAFT * 1.0
    innen = [kegelrohr(ri0, ri0, z_bohr - 1, z_i0 + 0.01, ya),
             kegelrohr(ri0, R_SCHAFT0 - T_SCHAFT, z_i0, z_i0 + dr + 0.01, ya),
             kegelrohr(R_SCHAFT0 - T_SCHAFT, ri1, z_i0 + dr, zi_end, ya),
             kegelrohr(ri1, 0.01, zi_end, zi_end + ri1, ya)]
    s = trimesh.boolean.difference([s, trimesh.boolean.union(innen, engine='manifold')], engine='manifold')
    return s, (z_kap, z_hals)


def r_aussen(z, z_kap, z_hals):
    return R_SCHAFT0 + (R_SCHAFT1 - R_SCHAFT0) * (z - z_kap) / (z_hals - z_kap)


def teile_schaft(s, L, z_bohr, ya, z_kap, z_hals):
    """Schaft in Stücke < H_MAX zerlegen. Stoß: unteres Stück innen auf STOSS_L zylindrisch, oberes Stück bekommt
    einen Zapfen (außen = Innenradius - 0,1)."""
    z_lo, z_hi = s.bounds[0, 2], s.bounds[1, 2]
    n = 1 if z_hi - z_lo <= H_MAX else int(np.ceil((z_hi - z_lo) / (H_MAX - STOSS_L)))
    if n <= 1:
        return [s]
    cuts = [z_lo + (z_hi - z_lo) * i / n for i in range(1, n)]
    stuecke = []
    grenzen = [z_lo - 1] + cuts + [z_hi + 1]
    for i in range(n):
        box = trimesh.creation.box(bounds=[[-50, ya - 50, grenzen[i]], [50, ya + 50, grenzen[i + 1]]])
        st = trimesh.boolean.intersection([s, box], engine='manifold')
        if i > 0:                                   # Zapfen nach unten
            zc = grenzen[i]
            ri = r_aussen(zc, z_kap, z_hals) - T_SCHAFT
            zap = kegelrohr(ri - 0.1, ri - 0.1, zc - STOSS_L, zc + 0.5, ya)
            zap_i = kegelrohr(ri - 0.1 - T_SCHAFT, ri - 0.1 - T_SCHAFT, zc - STOSS_L - 1, zc + 0.6, ya)
            st = trimesh.boolean.union([st, trimesh.boolean.difference([zap, zap_i], engine='manifold')], engine='manifold')
        if i < n - 1:                               # Aufnahme oben: Innenraum auf STOSS_L zylindrisch aufweiten
            zc = grenzen[i + 1]
            ri = r_aussen(zc, z_kap, z_hals) - T_SCHAFT
            st = trimesh.boolean.difference([st, kegelrohr(ri, ri, zc - STOSS_L - 0.3, zc + 1, ya)], engine='manifold')
        stuecke.append(st)
    return stuecke


def druck_kappe(k):
    r = k.copy(); r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]]); return r


def druck_stehend(s):
    r = s.copy(); r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]]); return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scan'); ap.add_argument('--out', default='out/')
    ap.add_argument('--laengen', default='200,400')
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    rho_tpu, rho_petg = 1.21, 1.27
    k, info, (z_tip, ya) = kappe(a.scan, 'kurz')
    k.export(os.path.join(a.out, 'stecknase_kurz_tpu_lage_scan.stl'))
    druck_kappe(k).export(os.path.join(a.out, 'stecknase_kurz_tpu.stl'))
    print('Körper (cm³):', info['koerper'])
    print(f"kurz: L {info['L']:.0f} mm ab Gesicht (Z 0), {k.volume/1000:.1f} cm³ = {k.volume/1000*rho_tpu:.1f} g TPU, wasserdicht {k.is_watertight}")
    kh, info, _ = kappe(a.scan, 'lang')
    kh.export(os.path.join(a.out, 'stecknase_kappe_tpu_lage_scan.stl'))
    druck_kappe(kh).export(os.path.join(a.out, 'stecknase_kappe_tpu.stl'))
    print(f"Kappe mit Steckhülse: {kh.volume/1000:.1f} cm³ = {kh.volume/1000*rho_tpu:.1f} g TPU, wasserdicht {kh.is_watertight}")
    for L in (float(x) for x in a.laengen.split(',')):
        s, (z_kap, z_hals) = schaft(L, info['z_bohr'], ya)
        stuecke = teile_schaft(s, L, info['z_bohr'], ya, z_kap, z_hals)
        g = s.volume / 1000 * rho_petg
        # Hebel: Schwerpunkt (Schaft + Kappe) vor dem Gesicht
        zs = s.center_mass[2]
        print(f"L {L:.0f}: Schaft {s.volume/1000:.1f} cm³ = {g:.1f} g PETG, Schwerpunkt Z {zs:.0f}, Moment etwa {g/1000*9.81*zs/1000*1000:.0f} N·mm, {len(stuecke)} Stück(e)")
        s.export(os.path.join(a.out, f'stecknase_{L:.0f}_schaft_lage_scan.stl'))
        for i, st in enumerate(stuecke):
            st = P.hauptkoerper(st)
            nm = f'stecknase_{L:.0f}_schaft' + (f'_teil{i+1}' if len(stuecke) > 1 else '') + '_petg.stl'
            d = druck_stehend(st); d.export(os.path.join(a.out, nm))
            print(f"   {nm}: Höhe {d.extents[2]:.0f} mm, wasserdicht {d.is_watertight}")


if __name__ == '__main__':
    main()
