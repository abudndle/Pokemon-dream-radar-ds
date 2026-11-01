"""Ensure title art generator, live renderer and hitboxes share pane geometry."""
import pathlib
import re

root=pathlib.Path(__file__).resolve().parents[1]
header=(root/"source/title_panes_generated.h").read_text()
renderer=(root/"source/main.c").read_text()
generator=(root/"tools/build_reference_ui.py").read_text()
block=header.split("dr_title_panes[4] = {",1)[1].split("};",1)[0]
rects=[tuple(map(int,row)) for row in re.findall(r"\{(\d+),(\d+),(\d+),(\d+)\}",block)]
assert len(rects)==4,rects
for i,(x,y,w,h) in enumerate(rects):
    assert 0<=x<256 and 0<=y<192
    assert 0<w<=256-x and 0<h<=192-y
    for xx,yy,ww,hh in rects[:i]:
        assert x+w<=xx or xx+ww<=x or y+h<=yy or yy+hh<=y
assert "const DrUiRect *r=&title_rows[i];" in renderer
assert "title_live_rects(title_rows);" in renderer
assert "dr_ui_title_rects(title_ui_scene," in renderer
assert "dr_ui_title_hit(title_rows,touch->px,touch->py)" in renderer
assert "dr_ui_scene_load(\"nitro:/title.drui\")" in renderer
assert "dr_title_hit(touch->px,touch->py)" in renderer
assert "for xx,yy,ww,hh in title_rects:" in generator
assert "title_header=(root/'source/title_panes_generated.h').read_text()" in generator
assert "re.findall(r'\\{(\\d+),(\\d+),(\\d+),(\\d+)\\}',pane_block)" in generator
print("PASS title art, renderer and touchscreen share 4 nonoverlapping panes")
