#!/usr/bin/env python3
"""Original, public-only ScanList pane snapshot to DS runtime integration."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from stage_title_ui import stage, SCAN_TARGET

snapshot = json.loads((ROOT / "ui_mapping/original_pane_geometry.json").read_text())
base = stage(snapshot, target=SCAN_TARGET)
assert base[:4] == b"DRUI"
# This is a synthetic CLPA sequence; never check original private curves in.
clip = {"frames": 12, "loops": False, "tracks": [{
    "pane": "L00", "property": "translate_y", "curve": 0,
    "keys": [
        {"frame": 0, "value": 157, "slope": 0},
        {"frame": 10, "value": 147, "slope": 0}
    ]
}]}
moving = stage(snapshot, [clip], target=SCAN_TARGET)
assert len(moving) > len(base)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    paths = [root / name for name in ("scanlist.drui", "moving.drui", "broken.drui")]
    for path, payload in zip(paths, (base, moving, moving[:-1])):
        path.write_bytes(payload)
    subprocess.run([str(ROOT / "build/test_scanlist_ui"), *(str(p) for p in paths)],
                   check=True)
# A malformed hierarchy cannot silently replace the original scene.
try:
    stage({"layouts": []}, target=SCAN_TARGET)
except ValueError:
    pass
else:
    raise AssertionError("missing ScanList layout accepted")
try:
    stage(snapshot, target="other.bclyt")
except ValueError:
    pass
else:
    raise AssertionError("unsupported original layout accepted")
print("PASS: original ScanList metadata, portable runtime bytes, animation and safe rejection")
