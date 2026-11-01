"""Regression tests: self-attested JSON cannot stand in for emulator artifacts."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_capture_milestone import audit_emulator_evidence

REQUIRED = (
    "cloud_search", "cloud_shot", "orb_collected", "sphere_encounter",
    "capture_reward", "results", "resume_radar", "save", "restart",
    "restored_reward",
)


def png_chunk(kind, body):
    return (struct.pack(">I", len(body)) + kind + body +
            struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff))


def screenshot(index):
    """Generate distinct valid 256x384 RGB PNGs without private game assets."""
    row = b"\x00" + bytes((index, 40, 200)) * 256
    raw = row * 384
    header = struct.pack(">IIBBBBB", 256, 384, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" +
            png_chunk(b"IHDR", header) +
            png_chunk(b"IDAT", zlib.compress(raw)) +
            png_chunk(b"IEND", b""))


def artifact(path, data):
    path.write_bytes(data)
    return {"path": path.name, "sha256": hashlib.sha256(data).hexdigest()}


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    report = root / "capture-report.json"
    assert audit_emulator_evidence(root, root)["status"] == "missing_report"
    report.write_text("{broken json")
    assert audit_emulator_evidence(root, root)["status"] == "invalid_report"

    log = artifact(root / "runtime.log",
                   b"Emulator: melonDS\nWindow XID: 1234\nROM: dream_radar.nds\n")
    good = {
        "emulator": "melonDS", "test_kind": "live_emulator_capture",
        "commit_sha": "a" * 40, "rom_sha256": "b" * 64,
        "stages": {stage: True for stage in REQUIRED},
        "runtime_log": log,
        "captures": {stage: artifact(root / f"stage-{i}.png", screenshot(i + 1))
                     for i, stage in enumerate(REQUIRED)},
    }

    def status(payload):
        report.write_text(json.dumps(payload))
        return audit_emulator_evidence(root, root)

    assert status(good)["status"] == "evidence_bundle_complete"
    assert status(good)["passed"]
    for stage in REQUIRED:
        invalid = copy.deepcopy(good)
        invalid["stages"][stage] = False
        assert not status(invalid)["passed"], stage
        del invalid["stages"][stage]
        assert not status(invalid)["passed"], stage
        invalid = copy.deepcopy(good)
        del invalid["captures"][stage]
        assert status(invalid)["status"] == "invalid_capture", stage
    for key, bad in (("emulator", "other"), ("test_kind", "navigation"),
                     ("commit_sha", "invalid"), ("rom_sha256", "invalid")):
        invalid = copy.deepcopy(good)
        invalid[key] = bad
        assert not status(invalid)["passed"], key
    invalid = copy.deepcopy(good)
    invalid["stages"]["save"] = 1
    assert not status(invalid)["passed"], "numeric truthiness must not pass"
    invalid = copy.deepcopy(good)
    invalid["captures"]["save"]["sha256"] = "0" * 64
    assert status(invalid)["status"] == "invalid_capture"
    invalid = copy.deepcopy(good)
    invalid["captures"]["save"]["path"] = "../untrusted.png"
    assert status(invalid)["status"] == "invalid_capture"
    invalid = copy.deepcopy(good)
    invalid["captures"]["save"]["path"] = "/tmp/untrusted.png"
    assert status(invalid)["status"] == "invalid_capture"
    invalid = copy.deepcopy(good)
    invalid["captures"]["save"] = artifact(root / "not-a-frame.png", b"not PNG")
    assert status(invalid)["status"] == "invalid_capture"
    invalid = copy.deepcopy(good)
    invalid["runtime_log"]["sha256"] = "0" * 64
    assert status(invalid)["status"] == "invalid_emulator_log"
    invalid = copy.deepcopy(good)
    invalid["runtime_log"] = artifact(root / "wrong.log", b"Fake screenshot notes")
    assert status(invalid)["status"] == "invalid_emulator_log"
    invalid = copy.deepcopy(good)
    for stage in REQUIRED:
        invalid["captures"][stage] = invalid["captures"][REQUIRED[0]]
    assert status(invalid)["status"] == "reused_captures"


    # A valid PNG container is not enough: the compressed image itself must
    # contain exactly the expected scanlines and legal per-row filter bytes.
    def invalid_png(png):
        invalid = copy.deepcopy(good)
        invalid["captures"]["save"] = artifact(root / "bad-pixels.png", png)
        assert status(invalid)["status"] == "invalid_capture"

    header = struct.pack(">IIBBBBB", 256, 384, 8, 2, 0, 0, 0)
    signature = b"\\x89PNG\\r\\n\\x1a\\n"
    def png_with_data(compressed, ihdr=header):
        return (signature + png_chunk(b"IHDR", ihdr) +
                png_chunk(b"IDAT", compressed) + png_chunk(b"IEND", b""))

    invalid_png(png_with_data(b"not zlib"))
    invalid_png(png_with_data(zlib.compress(b"too short")))
    invalid_png(png_with_data(zlib.compress(b"\\x05" + b"\\x00" * (256 * 3) +
                                            (b"\\x00" + b"\\x00" * (256 * 3)) * 383)))
    invalid_png(png_with_data(zlib.compress((b"\\x00" + b"\\x00" * 768) * 384) +
                              b"trailing garbage"))
    invalid_png(png_with_data(zlib.compress((b"\\x00" + b"\\x00" * 768) * 384),
                              struct.pack(">IIBBBBB", 4096, 384, 8, 2, 0, 0, 0)))
    # Different IDAT chunk partitioning is valid and must not be rejected.
    compressed = zlib.compress((b"\\x00" + b"\\x00" * 768) * 384)
    split = (signature + png_chunk(b"IHDR", header) +
             png_chunk(b"IDAT", compressed[:len(compressed)//2]) +
             png_chunk(b"IDAT", compressed[len(compressed)//2:]) +
             png_chunk(b"IEND", b""))
    assert len(split) > 0
    from audit_capture_milestone import _valid_png
    assert _valid_png(split)

print("PASS: emulator evidence requires real hashed PNGs, provenance log and stages")
