#!/usr/bin/env python3
"""Dream Orb aim must not consume the live TTL on redundant PNG decoding."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
script = (ROOT / "scripts/melonds_smoke.sh").read_text()
start = script.index("orb_aim_pulse() {")
end = script.index("\n}\n", start) + 2
function = script[start:end]
# Mock all external commands so this is a deterministic behavior test.
shell = """out=/tmp
aim_ds_key() { printf 'aim %s %s %s\\n' "$1" "$2" "$3"; }
snapshot() { printf 'snapshot %s\\n' "$1"; }
python3() { printf 'decode %s\\n' "$*"; }
""" + function + '\norb_aim_pulse initial-horizontal Right 0.150 0.06\norb_aim_pulse initial-vertical Up 0.100 0.06\n'
result = subprocess.run(["bash", "-c", shell], text=True, capture_output=True, check=True)
assert result.stdout.splitlines() == ["aim Right 0.150 0.06", "aim Up 0.100 0.06"], result.stdout

verbose = subprocess.run(["bash", "-c", "ORB_VERBOSE_CALIBRATION=1\n" + shell],
                         text=True, capture_output=True, check=True)
assert verbose.stdout.count("snapshot ") == 4, verbose.stdout
assert verbose.stdout.count("decode ") == 4, verbose.stdout
assert verbose.stdout.count("aim ") == 2, verbose.stdout

# The caller MUST still acquire a fresh Orb screenshot after movement and a
# second independent screenshot immediately before each actual A-button shot.
block = script[script.index('if [[ ! -f "$out/05-sphere-encounter.png" ]]'):script.index('# The initial pink cloud')]
assert 'snapshot 05-radar-orb-aimed' in block
assert 'snapshot "05-radar-orb-prefire-$sample"' in block
assert '--target orb' in block
assert 'within_safe_fire_radius' in block
assert 'press_ds_key z 0.12' in block
assert block.index('within_safe_fire_radius') < block.index('press_ds_key z 0.12')
assert 'ORB_VERBOSE_CALIBRATION:-0' in function
print("PASS: default Orb aiming avoids redundant PNG decodes; fresh prefire gate remains mandatory")
