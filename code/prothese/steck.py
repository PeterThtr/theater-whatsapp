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

NASE = (49.2, 31.8, 27.8)       # Frauennase (Verzerrung); mit --peter Peters eigener Scan ohne Verzerrung
SPIEL = -0.15                 # Pressung der Kappe (überall)
KLEMM = 0.6                   # zusätzliche Pressung seitlich (mm je Seite, gewichtet mit |n_x|), per --klemm
T_WAND, T_RAND = 2.4, 1.2     # Kappe kräftig (16.11.: 1,4/0,6 hielt nicht), zum Rand etwas dünner
PETER = False                 # --peter: Peters eigener Scan ohne Verzerrung (nur zum Ausprobieren; Ziel ist die Frauennase)
X_MITTE = -1.6                # Mittellinie der (verzerrten) Nase liegt bei x -1,6 (gemessen, sehr gleichmäßig) -> vor dem Spiegeln auf 0 schieben
Y_OBEN = 31.0                 # Oberkante der Kappe (Scan-Y, unverzerrt): über die Nasenwurzel (Y 25) hinaus, 16.11. (vorher 21; Prothese: 14)
STUETZ_B = 0.8                # Stützwand unter dem Rand (zum Abschneiden nach dem Druck)
STUETZ_Z = 0.0                # nur Randstücke hinter dieser Höhe (hinterer Rand auf den Wangen) bekommen eine Wand
STUETZ_X = 10.0               # ... und nur seitlich (|x| > STUETZ_X): über dem Nasenrücken keine Wand (Peter, 16.11.)
SEITE = +1                    # diese Hälfte (x > 0) wird gespiegelt -> symmetrische Kappe
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
ZAPFEN_ANGEFORMT = True       # Stöße: Zapfen oben am unteren Stück (sonst lose Steckhülsen)
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


def spiel_feld(N):
    """Abstand Kappe-Haut je Punkt (negativ = Pressung): überall SPIEL, seitlich (Flanken der Nase, |n_x| groß)
    zusätzlich bis KLEMM. So klemmt die Kappe die Nase von beiden Seiten wie eine Clownsnase."""
    return SPIEL - KLEMM * np.clip(np.abs(N[:, 0]), 0, 1) ** 1.5


def mitte_x(m):
    """Mittellinie der Nase in x: Mitte zwischen linker und rechter Hautfläche, 2–10 mm unter dem Rücken, Y −20…+20."""
    rs = m.ray
    xs = []
    for y in range(-20, 21, 3):
        loc, _, _ = rs.intersects_location([[0, y, 80]], [[0, 0, -1]])
        if not len(loc):
            continue
        zs = loc[:, 2].max()
        for dz in (2, 4, 6, 8, 10):
            o = [[0, y, zs - dz]]
            L, _, _ = rs.intersects_location(o, [[-1, 0, 0]]); R, _, _ = rs.intersects_location(o, [[1, 0, 0]])
            if len(L) and len(R):
                xs.append(0.5 * (L[:, 0].max() + R[:, 0].min()))
    return float(np.median(xs))


def kappe_basis(scan):
    if not getattr(P, '_gemorpht', False):
        sx, sy, sz = (1.0, 1.0, 1.0) if PETER else P.morph_faktoren(*NASE)
        if not PETER:
            P.morph_konstanten(sx, sy, sz)
        P.OUTLINE_P = [(-9.5 * sx, Y_OBEN * sy), (9.5 * sx, Y_OBEN * sy)] + P.OUTLINE_P[2:]
        P._gemorpht = True
    A.T_WAND, A.T_RAND = T_WAND, T_RAND
    A.OUTLINE = P.OUTLINE_P; A.UNTEN_Z = P.UNTEN_Z_P
    m = A.lade(scan, 1.0)
    xm = mitte_x(m)                                 # Nasenmitte auf x = 0, sonst passt die gespiegelte Hälfte nicht
    m.apply_translation([-xm, 0.0, 0.0])
    print(f'Nasenmitte x {xm:.2f} -> 0')
    p = A.waehle_flaechen(m, 1.0)
    # wie A.baue_schale, aber mit ortsabhängiger Pressung
    trimesh.smoothing.filter_taubin(p, lamb=0.5, nu=-0.53, iterations=12)
    V = np.asarray(p.vertices); F = np.asarray(p.faces); nv = len(V)
    N = A.glatte_normalen(p)
    rv = np.array(sorted({a for a, b in A.randkanten(F)}))
    from scipy import sparse
    from scipy.sparse.csgraph import dijkstra
    E = p.edges_unique
    w = np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)
    G = sparse.coo_matrix((w, (E[:, 0], E[:, 1])), shape=(nv, nv)); G = (G + G.T).tocsr()
    d = dijkstra(G, indices=rv, min_only=True)
    t = T_RAND + (T_WAND - T_RAND) * np.clip(d / A.T_AUSLAUF, 0, 1)
    Vi = V + spiel_feld(N)[:, None] * N            # Innenfläche
    schale = A.verdicke(Vi, F, N, t, spiel=0.0)
    global RAND
    RAND = (Vi, F, N, t)
    pv = A.waehle_flaechen(m, 1.0, outline=P.NASEN_UMRISS, unten_frei=False)
    trimesh.smoothing.filter_taubin(pv, lamb=0.5, nu=-0.53, iterations=12)
    Vv = np.asarray(pv.vertices); Nv = A.glatte_normalen(pv)
    nase = A.verdicke(Vv + spiel_feld(Nv)[:, None] * Nv, np.asarray(pv.faces), np.tile([0.0, 0.0, -1.0], (len(Vv), 1)),
                      np.full(len(Vv), 60.0), spiel=0.0)
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
    k = symmetrisch_mit_stuetze(k)
    teile_k = sorted(k.split(only_watertight=False), key=lambda q: -abs(q.volume))
    info['koerper'] = [round(abs(q.volume) / 1000, 2) for q in teile_k[:4]]
    return P.hauptkoerper(k), info, (z_tip, ya)


def stuetzwand(z_bett):
    """Senkrechte Wand (Breite STUETZ_B) unter dem hinteren Rand bis zur Druckplatte z_bett. Oben 0,3 in den Rand
    eingebettet; wird nach dem Druck mit dem Messer am Rand entlang abgeschnitten."""
    V, F, N, t = RAND
    rand = A.randkanten(F)
    mitte = V + (0.5 * t)[:, None] * N              # V ist schon die Innenfläche
    keile = []
    for a_, b_ in rand:
        pa, pb = mitte[a_], mitte[b_]
        if max(pa[2], pb[2]) > STUETZ_Z or min(abs(pa[0]), abs(pb[0])) < STUETZ_X:
            continue
        d = pb[:2] - pa[:2]; l = np.linalg.norm(d)
        if l < 1e-6:
            continue
        n = np.array([-d[1], d[0]]) / l * STUETZ_B / 2
        e = d / l * 0.15                               # leicht überlappend, damit die Stücke verschmelzen
        unten = [np.r_[pa[:2] - e + n, z_bett], np.r_[pa[:2] - e - n, z_bett], np.r_[pb[:2] + e - n, z_bett], np.r_[pb[:2] + e + n, z_bett]]
        oben = [np.r_[pa[:2] - e + n, pa[2] + 0.3], np.r_[pa[:2] - e - n, pa[2] + 0.3], np.r_[pb[:2] + e - n, pb[2] + 0.3], np.r_[pb[:2] + e + n, pb[2] + 0.3]]
        keile.append(trimesh.convex.convex_hull(np.array(unten + oben)))
    return trimesh.boolean.union(keile, engine='manifold')


def symmetrisch_mit_stuetze(k):
    """Hälfte SEITE behalten und spiegeln (links = rechts), dazu die Stützwand bis zur Druckplatte."""
    groß = 200.0
    box = trimesh.creation.box(bounds=[[0.0, -groß, -groß], [groß, groß, groß]]) if SEITE > 0 else \
        trimesh.creation.box(bounds=[[-groß, -groß, -groß], [0.0, groß, groß]])
    halb = trimesh.boolean.intersection([k, box], engine='manifold')
    z_bett = float(halb.bounds[0, 2])
    w = stuetzwand(z_bett)
    w = trimesh.boolean.intersection([w, box], engine='manifold')
    halb = trimesh.boolean.union([halb, w], engine='manifold')
    return trimesh.boolean.union([halb, P.spiegeln_x(halb)], engine='manifold')


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
    """Schaft in Stücke < H_MAX zerlegen (glatte Schnitte). Verbunden werden die Stücke mit einzelnen Steckhülsen
    (Verbinder), die je STOSS_L tief in beide Stücke greifen und eingeklebt werden. (Die angeformten Zapfen der
    ersten Fassung hingen nicht am Stück und fielen beim Export weg, 16.11.)"""
    z_lo, z_hi = s.bounds[0, 2], s.bounds[1, 2]
    n = 1 if z_hi - z_lo <= H_MAX else int(np.ceil((z_hi - z_lo) / H_MAX))
    if n <= 1:
        return [s], []
    cuts = [z_lo + (z_hi - z_lo) * i / n for i in range(1, n)]
    grenzen = [z_lo - 1] + cuts + [z_hi + 1]
    stuecke = []
    for i in range(n):
        box = trimesh.creation.box(bounds=[[-50, ya - 50, grenzen[i]], [50, ya + 50, grenzen[i + 1]]])
        st = trimesh.boolean.intersection([s, box], engine='manifold')
        if ZAPFEN_ANGEFORMT and i < n - 1:
            st = trimesh.boolean.union([st, zapfen_oben(grenzen[i + 1], z_kap, z_hals, ya)], engine='manifold')
            assert len(st.split(only_watertight=False)) == 1, 'Zapfen hängt nicht am Stück'
        stuecke.append(st)
    if ZAPFEN_ANGEFORMT:
        return stuecke, []
    verbinder = [verbinder_huelse(r_aussen(zc, z_kap, z_hals) - T_SCHAFT) for zc in cuts]
    return stuecke, verbinder


def zapfen_oben(zc, z_kap, z_hals, ya, luft=0.25, fase=0.25):   # luft 0,075 war gedruckt zu stramm (16.11.)
    """Angeformter Zapfen oben auf dem unteren Stück (16.11.): Innen wird die Wand unter dem Stoß mit 45° bis auf
    die Zapfenwand verdickt (außen bleibt alles glatt, keine Fuge), darüber ein Rohr STOSS_L lang, außen = engste
    Bohrung des oberen Stücks (STOSS_L über dem Stoß) − luft, Einführfase oben. Wird stehend ohne Stützen gedruckt."""
    ri = r_aussen(zc, z_kap, z_hals) - T_SCHAFT                     # Bohrung am Stoß
    ra = r_aussen(zc + STOSS_L, z_kap, z_hals) - T_SCHAFT - luft     # Zapfen außen
    rz = ra - T_SCHAFT                                                # Zapfen innen
    c = ri - rz                                                       # 45°-Verdickung innen
    profil = np.array([[ri + 0.05, zc - c - 0.2], [ri + 0.05, zc + 0.01], [ra, zc + 0.01], [ra, zc + STOSS_L - fase],
                       [ra - fase, zc + STOSS_L], [rz, zc + STOSS_L], [rz, zc], [ri, zc - c - 0.2], [ri + 0.05, zc - c - 0.2]])
    m = trimesh.creation.revolve(profil, sections=128)
    m.apply_translation([0, ya, 0])
    return m


def verbinder_huelse(ri, luft=0.12, wand=0.8, fase=0.4):
    """Steckhülse für einen Stoß: außen = Bohrung am Stoß − Luft (die Bohrung wird nach vorn etwas enger, an der
    Spitze bleiben etwa 0,02), Länge 2 × STOSS_L, Einführfasen an beiden Enden. Stehend drucken."""
    ra = ri - luft
    h = 2 * STOSS_L
    pr = np.array([[ra - wand, 0], [ra - fase, 0], [ra, fase], [ra, h - fase], [ra - fase, h], [ra - wand, h], [ra - wand, 0]])
    return trimesh.creation.revolve(pr, sections=96)


def druck_kappe(k):
    r = k.copy(); r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]]); return r


def druck_stehend(s):
    r = s.copy(); r.apply_translation([-r.bounds.mean(0)[0], -r.bounds.mean(0)[1], -r.bounds[0, 2]]); return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scan'); ap.add_argument('--out', default='out/')
    ap.add_argument('--laengen', default='200,400')
    ap.add_argument('--klemm', default=None, help='zusätzliche seitliche Pressung in mm je Seite, z. B. 0.4 oder 0.4,0.8 (Dateien mit _klemmXX)')
    ap.add_argument('--nur-kappen', action='store_true')
    ap.add_argument('--wand-schaft', type=float, default=None, help='Wandstärke des Schafts (Standard 0,9)')
    ap.add_argument('--hmax', type=float, default=None, help='größte Teilhöhe des Schafts (A1 Mini 178, A1 250)')
    ap.add_argument('--peter', action='store_true', help='Peters eigener Scan ohne Verzerrung, Dateien mit _peter')
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    global PETER, H_MAX
    PETER = a.peter
    if a.hmax:
        H_MAX = a.hmax
    global T_SCHAFT
    if a.wand_schaft:
        T_SCHAFT = a.wand_schaft
    rho_tpu, rho_petg = 1.21, 1.27
    global KLEMM
    stufen = [None] if a.klemm is None else [float(x) for x in a.klemm.split(',')]
    for kl in stufen:
        if kl is not None:
            KLEMM = kl
        suf = ('_peter' if PETER else '') + ('' if kl is None else f'_klemm{int(round(kl * 10)):02d}')
        k, info, (z_tip, ya) = kappe(a.scan, 'kurz')
        k.export(os.path.join(a.out, f'stecknase_kurz_tpu{suf}_lage_scan.stl'))
        druck_kappe(k).export(os.path.join(a.out, f'stecknase_kurz_tpu{suf}.stl'))
        print(f"kurz{suf}: L {info['L']:.0f} mm ab Gesicht (Z 0), {k.volume/1000:.1f} cm³ = {k.volume/1000*rho_tpu:.1f} g TPU, "
              f"wasserdicht {k.is_watertight}, Körper {info['koerper']}")
        kh, info, _ = kappe(a.scan, 'lang')
        kh.export(os.path.join(a.out, f'stecknase_kappe_tpu{suf}_lage_scan.stl'))
        druck_kappe(kh).export(os.path.join(a.out, f'stecknase_kappe_tpu{suf}.stl'))
        print(f"Kappe mit Steckhülse{suf}: {kh.volume/1000:.1f} cm³ = {kh.volume/1000*rho_tpu:.1f} g TPU, wasserdicht {kh.is_watertight}")
    if a.nur_kappen:
        return
    for L in (float(x) for x in a.laengen.split(',')):
        s, (z_kap, z_hals) = schaft(L, info['z_bohr'], ya)
        stuecke, verbinder = teile_schaft(s, L, info['z_bohr'], ya, z_kap, z_hals)
        for i, v in enumerate(verbinder):
            nm = f'stecknase_{L:.0f}_verbinder{i+1}{i+2}.stl'
            v.export(os.path.join(a.out, nm))
            print(f"   {nm}: außen Ø{2*v.bounds[1,0]:.2f}, Länge {v.extents[2]:.0f}, wasserdicht {v.is_watertight}")
        g = s.volume / 1000 * rho_petg
        # Hebel: Schwerpunkt (Schaft + Kappe) vor dem Gesicht
        zs = s.center_mass[2]
        print(f"L {L:.0f}: Schaft {s.volume/1000:.1f} cm³ = {g:.1f} g PETG, Schwerpunkt Z {zs:.0f}, Moment etwa {g/1000*9.81*zs/1000*1000:.0f} N·mm, {len(stuecke)} Stück(e)")
        s.export(os.path.join(a.out, f'stecknase_{L:.0f}_schaft_lage_scan.stl'))
        for i, st in enumerate(stuecke):
            st = P.hauptkoerper(st)
            nm = f'stecknase_{L:.0f}_schaft' + (f'_wand{int(round(T_SCHAFT*10)):02d}' if T_SCHAFT != 0.9 else '') + (f'_teil{i+1}' if len(stuecke) > 1 else '') + '_petg.stl'
            d = druck_stehend(st); d.export(os.path.join(a.out, nm))
            print(f"   {nm}: Höhe {d.extents[2]:.0f} mm, wasserdicht {d.is_watertight}")


if __name__ == '__main__':
    main()
