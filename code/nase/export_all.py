import cadquery as cq, tele as t
tot=0
items=[("nase_segment1",t.segment(1))]+[(f"nase_segment{k}",t.segment(k)) for k in (2,3,4,5)]
items+=[(f"nase_ring{k}",t.ring(k)) for k in (2,3,4)]
items+=[("nase_kappe",t.cap()),("nase_fuss_fluegel",t.foot(True)),("nase_fuss_rund",t.foot(False))]
for n,s in items:
    assert s.isValid(), n
    t.export(s,n); g=s.Volume()/1000*1.27
    if n!="nase_fuss_rund": tot+=g
    bb=s.BoundingBox(); print(f"{n:20s} {g:5.2f} g  {bb.xlen:.1f}x{bb.ylen:.1f}x{bb.zlen:.1f}")
print("Summe ca. %.1f g"%tot)
L0=t.L; t.L=24.0
t.export(t.segment(3),"probe_segment3_kurz"); t.export(t.segment(4),"probe_segment4_kurz"); t.L=L0
parts,_=t.assembly(False); a=cq.Assembly()
for n,p in parts.items(): a.add(p,name=n)
a.save("out/nase_baugruppe_eingefahren.step")
parts,_=t.assembly(True); a=cq.Assembly()
for n,p in parts.items(): a.add(p,name=n)
a.save("out/nase_baugruppe_ausgefahren.step")
# Druckvarianten mit Opferfuss (A1 Mini: schmale Auflage hält sonst nicht)
for k in (1, 2, 3, 4, 5):
    t.export(t.segment(k, opfer=True), f"nase_segment{k}_opferfuss")
L0 = t.L; t.L = 24.0
t.export(t.segment(3, opfer=True), "probe_segment3_kurz_opferfuss")
t.export(t.segment(4, opfer=True), "probe_segment4_kurz_opferfuss"); t.L = L0
