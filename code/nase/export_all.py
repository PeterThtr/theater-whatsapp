"""Exportiert alle Teile als STL und STEP nach out/.
Profil Feder (Standard):  python3 export_all.py
Profil Draht:             TELE_PROFIL=draht python3 export_all.py     (Dateinamen mit nase_draht_ / probe_draht_)
"""
import cadquery as cq, tele as t
P = "nase_draht6_" if t.DRAHT6 else ("nase_draht_" if t.DRAHT else "nase_")
Q = "probe_draht6_" if t.DRAHT6 else ("probe_draht_" if t.DRAHT else "probe_")
tot = 0
items = [(f"{P}segment{k}", t.segment(k)) for k in range(1, t.N + 1)]
if t.RINGE:
    items += [(f"{P}ring{k}", t.ring(k)) for k in range(2, t.N)]
items += [(f"{P}kappe", t.cap())]
if not t.DRAHT6:          # draht6 läuft ohne Fuß (Taschenboden der Prothese ist der Anschlag)
    items += [(f"{P}fuss_fluegel", t.foot(True)), (f"{P}fuss_rund", t.foot(False))]
for n, s in items:
    assert s.isValid(), n
    t.export(s, n); g = s.Volume() / 1000 * 1.27
    if n != f"{P}fuss_rund": tot += g
    bb = s.BoundingBox(); print(f"{n:24s} {g:5.2f} g  {bb.xlen:.1f}x{bb.ylen:.1f}x{bb.zlen:.1f}")
print("Summe ca. %.1f g" % tot)
L0 = t.L; t.L = 24.0
t.export(t.segment(3), f"{Q}segment3_kurz"); t.export(t.segment(4), f"{Q}segment4_kurz"); t.L = L0
parts, _ = t.assembly(False); a = cq.Assembly()
for n, p in parts.items(): a.add(p, name=n)
a.save(f"out/{P}baugruppe_eingefahren.step")
parts, _ = t.assembly(True); a = cq.Assembly()
for n, p in parts.items(): a.add(p, name=n)
a.save(f"out/{P}baugruppe_ausgefahren.step")
# Druckvarianten mit Opferfuss (A1 Mini: schmale Auflage hält sonst nicht)
for k in range(1, t.N + 1):
    t.export(t.segment(k, opfer=True), f"{P}segment{k}_opferfuss")
L0 = t.L; t.L = 24.0
t.export(t.segment(3, opfer=True), f"{Q}segment3_kurz_opferfuss")
t.export(t.segment(4, opfer=True), f"{Q}segment4_kurz_opferfuss"); t.L = L0
