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
assert report["invalid_layout_sources"]==[]
assert report["unmatched_layout_sources"]==[]

assert sum(x["source_bclyt"] for x in report["layouts"])==1
assert any(x["layout"]=="MnGm_S_Menu.bclyt" and x["source_bclyt"] for x in report["layouts"])
with tempfile.TemporaryDirectory() as d:
    empty=pathlib.Path(d)
    no_sources=audit(snapshot,empty)
    assert no_sources["missing_layout_sources"]==22
    assert no_sources["bundled_layout_sources"]==0
    fake=empty/"damaged.bclyt"
    fake.write_bytes(b"not a CLYT file")
    corrupt=audit(snapshot,empty)
    assert corrupt["invalid_layout_sources"]==["damaged.bclyt"]
    assert corrupt["unmatched_layout_sources"]==["damaged.bclyt"]
    # A valid CLYT magic + little-endian BOM must not be flagged as corrupt.
    fake.write_bytes(b"CLYT\\xff\\xfe\\x14\\x00")
    valid=audit(snapshot,empty)
    assert valid["invalid_layout_sources"]==[]
print("PASS: original UI source inventory distinguishes 22 snapshots from bundled sources")
