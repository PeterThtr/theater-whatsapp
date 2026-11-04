"""Teleskop-Nase V2: 5 Segmente (Profil draht6: 6 Segmente ohne Ringe), integrierte Bünde (unten aussen) und Lippen (oben innen),
aufgeklebte Anschlagringe (oben, für das Einziehen), Kappe mit Knotenfenster, Fuss mit Flügeln.
Koordinaten: z = Achse, z=0 = Oberseite Fussplatte = Unterkante Segment 1. Masse in mm.
"""
import math, os, sys
import cadquery as cq

# Profil: "feder" (Druckfeder + Schnur, Bohrung Ø 10,8 in Segment 5) oder "draht" (Schub-Zug-Draht Ø 1,5, viel schlanker).
# Umschalten per Umgebungsvariable: TELE_PROFIL=draht python3 export_all.py
# "draht6": 6 Segmente bei gleichem Segment 1 (Außen-Ø 19,8, passt in die gedruckte Prothese), Wand 0,8, Ringspalt 0,6,
# ohne Ringe (eingefahren stehen alle Segmente unten am Anschlag), kürzere Segmente bei gleichem Hub.
PROFIL = os.environ.get("TELE_PROFIL", "feder")
# "draht2": 5 Segmente wie "draht", aber ohne Ringe und Fuß, mit breiter Halbkugel-Kappe (nimmt beim Einziehen alle
# Segmente mit) und mehr Spiel an der Fuge Segment 3/4 (Peter, 3.11.: dort zu viel Reibung).
DRAHT6 = PROFIL == "draht6"
DRAHT2 = PROFIL == "draht2"
DRAHT = PROFIL in ("draht", "draht6", "draht2")
N = 6 if DRAHT6 else 5           # Anzahl Segmente
RINGE = not (DRAHT6 or DRAHT2)   # aufgeklebte Ringe zum geordneten Einziehen
FUSS = RINGE                     # ohne Ringe: kein Fuß, der Taschenboden der Prothese ist der Anschlag
KAPPE_BREIT = DRAHT6 or DRAHT2   # breite Kappe statt Ringe

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# ---------- Parameter
S = 0.15          # radiales Spiel an Lippe und Bund
G = 0.6 if DRAHT6 else 0.8   # Ringspalt zwischen Rohr k+1 aussen und Rohr k innen
C = G - S         # Bundüberstand = Lippenüberstand (0.65)
S_FUGE = {3: 0.25} if DRAHT2 else {}   # abweichendes radiales Spiel je Fuge k/k+1 (draht2: Fuge 3/4)


def spiel(k):
    """Radiales Spiel an der Fuge zwischen Segment k (außen) und k+1 (innen)."""
    return S_FUGE.get(k, S)
BAND = 5.0        # Lippenlänge (gerade)
CH = 10.0         # Bundhöhe
FUN = 0.6         # Einlauffase innen unten (Feder)
L = 52.5 if DRAHT6 else 62.0      # Länge Segmente 2..N (draht6: 5 Fugen × 37,2 = 186 mm Hub)
L1 = L if DRAHT6 else 63.5         # Länge Segment 1 (ohne Ring 2 braucht es keine Überlänge)
W = [None, 1.2, 0.8, 0.8, 0.8, 0.8, 0.8] if DRAHT6 else [None, 1.2, 1.0, 1.0, 1.0, 0.8 if DRAHT else 1.0]   # Wandstärken
RI5 = 1.7 if DRAHT else 5.4   # Bohrung Segment 5: Draht Ø 1,5 (Ø 3,4 Bohrung) bzw. Feder AD 10
WT = 1.2          # Ringdicke
WC = 0.7          # Ringfase / Senkung
WB = 0.2          # Ringbohrung-Spiel (radial)
GLUE = 0.05
# Opferfuss (Druckhilfe, wird nach dem Druck abgeschnitten)
OF_FASE = 0.6     # Aussenfase unten am Bund (statt 0.3); der Abtrennrest bleibt innerhalb dieser Fase
OF_STEG = 0.35    # Dicke des Abtrennstegs (2-3 Schichten)
OF_NUT = 1.0      # radiale Breite des Stegs vor der dicken Scheibe
OF_DICKE = 0.8    # Dicke der Scheibe
OF_BREITE = 7.0   # Scheibe reicht bis Bund-Radius + OF_BREITE

# Radien von innen nach aussen
RI = [None] * (N + 1); RO = [None] * (N + 1)
RI[N] = RI5; RO[N] = RI5 + W[N]
for k in range(N - 1, 0, -1):
    RI[k] = RO[k + 1] + G
    RO[k] = RI[k] + W[k]


def revolve(pts):
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def segment(k, opfer=False, fase=None):
    """opfer=True: mit Opferfuss (druckfertig). fase: Aussenfase unten (Standard 0.3, mit Opferfuss OF_FASE)."""
    if fase is None:
        fase = OF_FASE if opfer else 0.3
    Lk = L1 if k == 1 else (L + KAPPE_MUFFE if (KAPPE_BREIT and k == N) else L)
    ri, ro = RI[k], RO[k]
    p = []
    # innen unten
    if k == 1:
        p += [(ri, 0.0)]
    else:
        p += [(ri + FUN, 0.0), (ri, FUN)]
    # innen hoch
    if k <= N - 1:
        rl = RO[k + 1] + spiel(k)   # Lippenbohrung
        p += [(ri, Lk - BAND - (ri - rl)), (rl, Lk - BAND)]     # 45°-Kegel, Überstand ri - rl (= C bei Standardspiel)
        if k == 1:
            p += [(rl, Lk - WC), (rl + WC, Lk)]      # Senkung für Ring 2
        else:
            p += [(rl, Lk)]
    else:
        p += [(ri, Lk - 0.6), (ri + 0.6, Lk)]         # Senkung für Kappe
    # aussen runter
    p += [(ro, Lk)]
    if k == 1:
        p += [(ro, fase), (ro - fase, 0.0)]
        rb = ro
    else:
        cb = G - spiel(k - 1)       # Bundüberstand an der Fuge k-1/k
        p += [(ro, CH + cb), (ro + cb, CH), (ro + cb, fase), (ro + cb - fase, 0.0)]
        rb = ro + cb
    s = revolve(p)
    if opfer:
        s = s.fuse(opferfuss(rb, fase))
        assert s.isValid() and len(s.Solids()) == 1, "Opferfuss nicht verbunden"
    return s


def opferfuss(rb, fase):
    """Flache Scheibe um die Unterkante. Verbunden nur über einen dünnen Steg (OF_STEG),
    der an der Aussenfase ansetzt; der Rest nach dem Abschneiden liegt innerhalb der Fase,
    also nicht auf der Gleitfläche r = rb."""
    r0 = rb - fase - 0.1          # leicht ins Teil hinein, damit fuse einen Körper ergibt
    p = [(r0, 0.0), (rb + OF_BREITE, 0.0), (rb + OF_BREITE, OF_DICKE), (rb + OF_NUT, OF_DICKE),
         (rb + OF_NUT, OF_STEG), (r0, OF_STEG)]
    return revolve(p)


def ring(k):
    """Anschlagring auf Segment k (k=2..4): flach gedruckt, Fase unten aussen, Senkung oben innen."""
    rb = RO[k + 1] + WB
    ro = RO[k]
    p = [(rb, 0.0), (ro, 0.0), (ro + WC, WC), (ro + WC, WT), (rb + WC, WT), (rb, WT - WC)]
    return revolve(p)


CAP_R = RO[N] + WC     # 7.1
# draht2/draht6: breite Halbkugel-Kappe, die beim Einziehen alle Segmente 2..N-1 mitnimmt (Ø = Segment 2 außen).
# Statt Zapfen eine Muffe: das innerste Segment (um KAPPE_MUFFE länger) steckt darin; flache Seite liegt auf der Druckplatte.
KAPPE_R = RO[2] if KAPPE_BREIT else None   # draht6: 8,1 -> Ø 16,2; draht2: 7,9 -> Ø 15,8
KAPPE_MUFFE = 3.0                     # Tiefe der Muffe = Überlänge von Segment 6
KAPPE_BAND = 0.6                      # zylindrischer Rand unter der Halbkugel
SHAFT_R = RI5 - 0.1
SHAFT_BOT = -7.95


def cap_breit(schnur=False):
    """z = 0 = flache Unterseite (liegt eingefahren auf den Stirnflächen von Segment 2..N-1)."""
    R = KAPPE_R
    p = [(RO[N] + GLUE + 0.3, 0.0), (R - 0.3, 0.0), (R, 0.3), (R, KAPPE_BAND)]
    n = 32
    for i in range(1, n + 1):
        a = math.radians(90 * i / n)
        p.append((R * math.cos(a), KAPPE_BAND + R * math.sin(a)))
    p[-1] = (0.0, KAPPE_BAND + R)
    rm = RO[N] + GLUE                       # Muffe Ø 5,1 für Segment 6 (Klebespalt 0,05)
    p += [(0.0, KAPPE_MUFFE), (rm, KAPPE_MUFFE), (rm, 0.3)]
    s = revolve(p)
    if schnur:
        # Schnur statt Draht: Durchgangsloch Ø 1,2 bis zum Scheitel, oben Senkung für den Knoten (Ø 3,6, 1,5 tief).
        # Die Feder (Außen-Ø 3,0) stützt sich auf den Muffenboden um das Loch.
        top = KAPPE_BAND + R
        hole = cq.Workplane("XY").workplane(offset=KAPPE_MUFFE - 0.1).circle(0.6).extrude(top - KAPPE_MUFFE + 0.2).val()
        senk = cq.Solid.makeCone(0.6, 1.8, 1.5, cq.Vector(0, 0, top - 1.5), cq.Vector(0, 0, 1))
        return s.cut(hole).cut(senk)
    # Sackloch Ø 1,7 für den Draht vom Muffenboden nach oben (1,2 mm Restwand unter dem Scheitel)
    top = KAPPE_BAND + R - 1.2
    hole = cq.Workplane("XY").workplane(offset=KAPPE_MUFFE - 0.1).circle(0.85).extrude(top - KAPPE_MUFFE + 0.1).val()
    return s.cut(hole)


def federscheibe():
    """PETG-Scheibe für den Taschenboden der Prothese (Feder + Schnur): Auflage der Feder und harter Anschlag der
    Segmente beim Einfahren. Ø 18,8 passt von vorn durch die Prothesenbohrung Ø 19,3. Mitte: Loch Ø 1,5 für die
    Schnur mit Einlauf unten, oben eine Mulde Ø 3,4 × 0,4 und ein Mittelstift Ø 2,0 × 2,5, der in die Feder
    (Außen-Ø 3,0, innen etwa 2,3) ragt und sie unten festhält. Schnurloch Ø 1,0 durch den Stift (Schnur bis etwa 0,6)."""
    t, r = 1.2, 9.4
    rs, hs, rl = 1.0, 2.5, 0.5          # Stift-Radius, Stifthöhe über der Mulde, Schnurloch-Radius
    zm = t - 0.4                        # Boden der Mulde
    s = revolve([(rl, 0.0), (r - 0.3, 0.0), (r, 0.3), (r, t), (1.7, t), (1.7, zm), (rs, zm),
                 (rs, zm + hs - 0.3), (rs - 0.3, zm + hs), (rl, zm + hs)])
    fun = cq.Solid.makeCone(1.0, rl, 0.5, cq.Vector(0, 0, -0.01), cq.Vector(0, 0, 1))
    return s.cut(fun)


def cap():
    if KAPPE_BREIT:
        return cap_breit()
    # z=0 = Stirnfläche Segment 5
    p = [(0, SHAFT_BOT), (SHAFT_R - 0.3, SHAFT_BOT), (SHAFT_R, SHAFT_BOT + 0.3),
         (SHAFT_R, -0.65), (RI5 + 0.6, GLUE), (RO[N], GLUE), (CAP_R, GLUE + WC), (CAP_R, 1.05)]
    z0 = 1.05
    n = 24
    for i in range(1, n + 1):
        a = math.radians(90 * i / n)
        p.append((CAP_R * math.cos(a), z0 + CAP_R * math.sin(a)))
    p[-1] = (0.0, z0 + CAP_R)
    s = revolve(p)
    if DRAHT:
        # Sackloch Ø 1,7 von unten für den Draht (mit 2K-Epoxid oder Sekundenkleber einkleben, 11 mm tief)
        hole = cq.Workplane("XY").workplane(offset=SHAFT_BOT - 0.1).circle(0.85).extrude(11.55).val()
        cone = cq.Solid.makeCone(1.3, 0.85, 0.45, cq.Vector(0, 0, SHAFT_BOT), cq.Vector(0, 0, 1))
        return s.cut(hole).cut(cone)
    # Knotenfenster: Tropfenform quer (Achse x), Spitze oben
    zc = SHAFT_BOT + 1.6 + 1.75
    r = 1.75
    # Tropfen als Polygon
    pts = []
    for i in range(0, 271, 10):
        a = math.radians(135 + i)
        pts.append((r * math.cos(a), zc + r * math.sin(a)))
    pts.append((0, zc + r * math.sqrt(2)))
    win = cq.Workplane("YZ").workplane(offset=-10).polyline(pts).close().extrude(20).val()
    s = s.cut(win)
    # zentrales Schnurloch + Einlauf
    hole = cq.Workplane("XY").workplane(offset=SHAFT_BOT - 0.1).circle(0.6).extrude(zc - SHAFT_BOT + 0.1).val()
    cone = cq.Solid.makeCone(1.0, 0.6, 0.4, cq.Vector(0, 0, SHAFT_BOT), cq.Vector(0, 0, 1))
    s = s.cut(hole).cut(cone)
    return s


# Fuss
PLATE_T = 1.5
CUP_RI = RO[1] + GLUE
CUP_RO = (CUP_RI + 1.0) if DRAHT else 14.9
CUP_H = 4.0
BOSS_R, BOSS_H = (2.5, 1.4) if DRAHT else (4.0, 2.0)      # Federdorn bzw. kurze Drahtführung (bleibt unter Segment 5: Unterkante bei z = 1,7)
WING_TIP = 24.0
WING_HW = 5.5
HOLES_X = (17.6, 21.0)


def foot(wings=True):
    from shapely.geometry import Point, box as sbox
    from shapely.ops import unary_union
    shp = Point(0, 0).buffer(CUP_RO, 128)
    if wings:
        cx = WING_TIP - WING_HW
        for sgn in (1, -1):
            shp = unary_union([shp, sbox(min(0, sgn * cx), -WING_HW, max(0, sgn * cx), WING_HW),
                               Point(sgn * cx, 0).buffer(WING_HW, 64)])
        shp = shp.buffer(1.5, 64).buffer(-1.5, 64)   # Innenecken runden
    xy = list(shp.exterior.coords)[:-1]
    plate = cq.Workplane("XY").workplane(offset=-PLATE_T).polyline(xy).close().extrude(PLATE_T).val()
    if wings:
        for sgn in (1, -1):
            for hx in HOLES_X:
                plate = plate.cut(cq.Workplane("XY").workplane(offset=-PLATE_T - 1).center(sgn * hx, 0)
                                  .circle(1.5).extrude(PLATE_T + 2).val())
    cup = revolve([(CUP_RI, 0.0), (CUP_RO, 0.0), (CUP_RO, CUP_H - 0.3), (CUP_RO - 0.3, CUP_H),
                   (CUP_RI + 0.3, CUP_H), (CUP_RI, CUP_H - 0.3)])
    boss = revolve([(0.0, 0.0), (BOSS_R, 0.0), (BOSS_R, BOSS_H - 0.4), (BOSS_R - 0.4, BOSS_H), (0.0, BOSS_H)])
    s = plate.fuse(cup) if not FUSS else plate.fuse(cup).fuse(boss)   # ohne Fuß (draht2/6): kein Dorn (Fuß nur Anschlagebene, Segment 6 steht unten auf)
    hr = 0.9 if DRAHT else 0.75                  # Loch für Draht Ø 1,8 bzw. Schnur Ø 1,5
    hole = cq.Workplane("XY").workplane(offset=-PLATE_T - 1).circle(hr).extrude(PLATE_T + BOSS_H + 2).val()
    fun_top = cq.Solid.makeCone(hr, hr + 0.55, 0.55, cq.Vector(0, 0, BOSS_H - 0.55), cq.Vector(0, 0, 1))
    fun_bot = cq.Solid.makeCone(hr + 0.4, hr, 0.4, cq.Vector(0, 0, -PLATE_T), cq.Vector(0, 0, 1))
    return s.cut(hole).cut(fun_top).cut(fun_bot).clean()


# ---------- Positionen
def tops_retracted():
    """Unterkanten B[k] eingefahren."""
    if not RINGE:                 # ohne Ringe: alle Segmente stehen unten auf dem Anschlag (Fußplatte bzw. Taschenboden)
        return {k: 0.0 for k in range(1, N + 1)}
    T = {1: L1}
    T[2] = L1 - WC - S   # Ring 2 (Unterkante = T2+GLUE) sitzt mit GLUE Abstand in der Senkung von Segment 1
    T[3] = T[2] + (WT - WC) - WB + GLUE  # = +0.35
    T[4] = T[3] + (WT - WC) - WB + GLUE
    T[5] = T[4] + (WT - WC) - WB + GLUE         # Kappe: Fase beginnt GLUE über Stirn
    B = {1: 0.0}
    for k in (2, 3, 4, 5):
        B[k] = T[k] - L
    return B


def stop_offset(k_outer):
    """Unterkante innen minus Unterkante aussen, wenn Bundkegel auf Lippenkegel liegt."""
    Lk = L1 if k_outer == 1 else L
    # Bundkegel: z = Bi + CH + (RO_i + C - r);  Lippenkegel: z = Ba + Lk - BAND - C + (RI_a - r), RI_a = RO_i + G
    c = G - spiel(k_outer)
    return Lk - BAND - c + G - CH - c


def assembly(extended=False, gap=0.0):
    B = tops_retracted()
    if extended:
        Bx = {1: 0.0}
        for k in range(2, N + 1):
            Bx[k] = Bx[k - 1] + stop_offset(k - 1) - gap
        B = Bx
    parts = {}
    parts["fuss"] = foot().translate(cq.Vector(0, 0, 0))
    for k in range(1, N + 1):
        parts[f"seg{k}"] = segment(k).translate(cq.Vector(0, 0, B[k]))
    if RINGE:
        for k in range(2, N):
            top = B[k] + L
            parts[f"ring{k}"] = ring(k).translate(cq.Vector(0, 0, top + GLUE))
    parts["kappe"] = cap().translate(cq.Vector(0, 0, B[N] + L))
    return parts, B


def export(shape, name, rot=None):
    s = shape
    if rot == "flip":
        s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180)
    bb = s.BoundingBox()
    s = s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))
    cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, name + ".stl"), tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, name + ".step"))
    return s


if __name__ == "__main__":
    for k in range(1, N + 1):
        print(f"Seg {k}: RI {RI[k]:.2f}  RO {RO[k]:.2f}  (Ø {2*RO[k]:.1f})", end="")
        if k >= 2: print(f"  Bund Ø {2*(RO[k]+G-spiel(k-1)):.2f}", end="")
        if k <= N - 1: print(f"  Lippe Ø {2*(RO[k+1]+spiel(k)):.2f}", end="")
        print()
    print("Hub je Fuge:", [round(stop_offset(k) - (tops_retracted()[k + 1] - tops_retracted()[k]), 2) for k in range(1, N)])
