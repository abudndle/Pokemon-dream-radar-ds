import json
import pathlib
import sys
import tempfile

root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"tools"))
from audit_original_ui import audit

snapshot=root/"ui_mapping/original_pane_geometry.json"
sources=root/"ui_mapping/original_ui"
report=audit(snapshot,sources)
assert report["extracted_layouts"]==22
assert report["bundled_layout_sources"]==1
assert report["missing_layout_sources"]==21
assert report["bundled_animation_sources"]==0
assert sum(x["source_bclyt"] for x in report["layouts"])==1
assert any(x["layout"]=="MnGm_S_Menu.bclyt" and x["source_bclyt"] for x in report["layouts"])
with tempfile.TemporaryDirectory() as d:
    empty=pathlib.Path(d)
    no_sources=audit(snapshot,empty)
    assert no_sources["missing_layout_sources"]==22
    assert no_sources["bundled_layout_sources"]==0
print("PASS: original UI source inventory distinguishes 22 snapshots from bundled sources")
