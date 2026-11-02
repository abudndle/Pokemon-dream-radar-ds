#!/usr/bin/env python3
"""Synthetic subprocess regression for bounded emulator cleanup.

This exercises only the shell cleanup trap, not a live melonDS save.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "scripts/melonds_smoke.sh").read_text()
start = source.index("cleanup(){\n")
end = source.index("\ntrap cleanup EXIT", start)
function = source[start:end]

with tempfile.TemporaryDirectory() as temporary:
    for mode in ("cooperative", "ignores_term", "gui_close"):
        out = Path(temporary) / mode
        out.mkdir()
        script = """set -euo pipefail
out="$1"
bash -c 'if [[ "$1" == ignores_term ]]; then trap "" TERM; else trap "exit 0" TERM; fi; while :; do sleep 0.1; done' bash "$2" &
pid=$!
printf 'Emulator launcher PID: %s\\n' "$pid" >"$out/runtime.log"
if [[ "$2" == gui_close ]]; then
  window=123
  xdotool() { [[ "$1" == windowclose ]] && kill -TERM "$pid"; }
fi
FUNCTION
trap cleanup EXIT
sleep 0.3
""".replace("FUNCTION", function)
        result = subprocess.run(["bash", "-c", script, "test", str(out), mode],
                                text=True, capture_output=True, timeout=12)
        assert result.returncode == 0, (mode, result.stderr)
        log = (out / "runtime.log").read_text()
        assert "terminated" in log and "still running" not in log, (mode, log)
        if mode == "ignores_term":
            assert "force-killed" in log, log
        else:
            assert "force-killed" not in log, log
        if mode == "gui_close":
            assert "GUI close requested" in log, log
print("PASS: emulator cleanup is bounded for cooperative, GUI-closed and SIGTERM-resistant processes")
