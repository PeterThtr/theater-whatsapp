"""Teleskop-Nase V2: 5 Segmente, integrierte Bünde (unten aussen) und Lippen (oben innen),
aufgeklebte Anschlagringe (oben, für das Einziehen), Kappe mit Knotenfenster, Fuss mit Flügeln.
Koordinaten: z = Achse, z=0 = Oberseite Fussplatte = Unterkante Segment 1. Masse in mm.
"""
import math, os, sys
import cadquery as cq

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# ---------- Parameter
S = 0.15          # radiales Spiel an Lippe und Bund
G = 0.8           # Ringspalt zwischen Rohr k+1 aussen und Rohr k innen
C = G - S         # Bundüberstand = Lippenüberstand (0.65)
BAND = 5.0        # Lippenlänge (gerade)
CH = 10.0         # Bundhöhe
FUN = 0.6         # Einlauffase innen unten (Feder)
L = 62.0          # Länge Segmente 2..5
L1 = 63.5         # Länge Segment 1
W = [None, 1.2, 1.0, 1.0, 1.0, 1.0]   # Wandstärken
RI5 = 5.4         # Bohrung Segment 5 (Feder AD 10)
WT = 1.2          # Ringdicke
WC = 0.7          # Ringfase / Senkung
WB = 0.2          # Ringbohrung-Spiel (radial)
GLUE = 0.05

# Radien von innen nach aussen
RI = [None] * 6; RO = [None] * 6
RI[5] = RI5; RO[5] = RI5 + W[5]
for k in (4, 3, 2, 1):
    RI[k] = RO[k + 1] + G
    RO[k] = RI[k] + W[k]


def revolve(pts):
    return cq.Workplane("XZ").polyline(pts).close().revolve(360, (0, 0, 0), (0, 1, 0)).val()


def segment(k):
    Lk = L1 if k == 1 else L
    ri, ro = RI[k], RO[k]
    p = []
    # innen unten
    if k == 1:
        p += [(ri, 0.0)]
    else:
        p += [(ri + FUN, 0.0), (ri, FUN)]
    # innen hoch
    if k <= 4:
        rl = RO[k + 1] + S          # Lippenbohrung
        p += [(ri, Lk - BAND - C), (rl, Lk - BAND)]
        if k == 1:
            p += [(rl, Lk - WC), (rl + WC, Lk)]      # Senkung für Ring 2
        else:
            p += [(rl, Lk)]
    else:
        p += [(ri, Lk - 0.6), (ri + 0.6, Lk)]         # Senkung für Kappe
    # aussen runter
    p += [(ro, Lk)]
    if k == 1:
        p += [(ro, 0.3), (ro - 0.3, 0.0)]
    else:
        p += [(ro, CH + C), (ro + C, CH), (ro + C, 0.3), (ro + C - 0.3, 0.0)]
    return revolve(p)


def ring(k):
    """Anschlagring auf Segment k (k=2..4): flach gedruckt, Fase unten aussen, Senkung oben innen."""
    rb = RO[k + 1] + WB
    ro = RO[k]
    p = [(rb, 0.0), (ro, 0.0), (ro + WC, WC), (ro + WC, WT), (rb + WC, WT), (rb, WT - WC)]
    return revolve(p)


CAP_R = RO[5] + WC     # 7.1
SHAFT_R = RI5 - 0.1
SHAFT_BOT = -7.95


def cap():
    # z=0 = Stirnfläche Segment 5
    p = [(0, SHAFT_BOT), (SHAFT_R - 0.3, SHAFT_BOT), (SHAFT_R, SHAFT_BOT + 0.3),
         (SHAFT_R, -0.65), (RI5 + 0.6, GLUE), (RO[5], GLUE), (CAP_R, GLUE + WC), (CAP_R, 1.05)]
    z0 = 1.05
    n = 24
    for i in range(1, n + 1):
        a = math.radians(90 * i / n)
        p.append((CAP_R * math.cos(a), z0 + CAP_R * math.sin(a)))
    p[-1] = (0.0, z0 + CAP_R)
    s = revolve(p)
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
CUP_RO = 14.9
CUP_H = 4.0
BOSS_R, BOSS_H = 4.0, 2.0
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
    s = plate.fuse(cup).fuse(boss)
    hole = cq.Workplane("XY").workplane(offset=-PLATE_T - 1).circle(0.75).extrude(PLATE_T + BOSS_H + 2).val()
    fun_top = cq.Solid.makeCone(0.75, 1.3, 0.55, cq.Vector(0, 0, BOSS_H - 0.55), cq.Vector(0, 0, 1))
    fun_bot = cq.Solid.makeCone(1.15, 0.75, 0.4, cq.Vector(0, 0, -PLATE_T), cq.Vector(0, 0, 1))
    return s.cut(hole).cut(fun_top).cut(fun_bot).clean()


# ---------- Positionen
def tops_retracted():
    """Unterkanten B[k] eingefahren."""
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
    return Lk - BAND - C + G - CH - C


def assembly(extended=False, gap=0.0):
    B = tops_retracted()
    if extended:
        Bx = {1: 0.0}
        for k in (2, 3, 4, 5):
            Bx[k] = Bx[k - 1] + stop_offset(k - 1) - gap
        B = Bx
    parts = {}
    parts["fuss"] = foot().translate(cq.Vector(0, 0, 0))
    for k in (1, 2, 3, 4, 5):
        parts[f"seg{k}"] = segment(k).translate(cq.Vector(0, 0, B[k]))
    for k in (2, 3, 4):
        top = B[k] + L
        parts[f"ring{k}"] = ring(k).translate(cq.Vector(0, 0, top + GLUE))
    parts["kappe"] = cap().translate(cq.Vector(0, 0, B[5] + L))
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
    for k in range(1, 6):
        print(f"Seg {k}: RI {RI[k]:.2f}  RO {RO[k]:.2f}  (Ø {2*RO[k]:.1f})", end="")
        if k >= 2: print(f"  Bund Ø {2*(RO[k]+C):.2f}", end="")
        if k <= 4: print(f"  Lippe Ø {2*(RO[k+1]+S):.2f}", end="")
        print()
    print("Hub je Fuge:", [round(stop_offset(k) - (tops_retracted()[k + 1] - tops_retracted()[k]), 2) for k in (1, 2, 3, 4)])
