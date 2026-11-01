#!/usr/bin/env python3
"""Audit and optionally execute Dream Radar capture milestone host checks.

No private Nintendo assets are required. This is NOT an emulator acceptance test.
"""
import argparse
import json
import pathlib
import subprocess
import sys

REQUIRED = {
    "source/game.c": "portable gameplay rules",
    "tests/test_radar_resume.c": "scan resume",
    "tests/test_capture_milestone_end_to_end.c": "complete capture and persistent reward acceptance",
    "tests/test_dream_orb_entities.c": "orb collection",
    "tests/test_capture_profiles.c": "capture profile",
    "tests/test_gameplay_save_roundtrip.c": "save reload",
    "tests/test_melonds_navigation.py": "screenshot heading recognition",
    "scripts/melonds_smoke.sh": "real emulator navigation smoke",
    "tools/verify_melonds_navigation.py": "recognize native DS emulator frames",
    ".github/workflows/capture-host-acceptance.yml": "CI acceptance evidence",
    "docs/feature_parity.json": "feature parity tracking",
    "source/main.c": "real DS input and display integration",
    "tests/test_capture_emulator_evidence.py": "reject incomplete emulator evidence",
}

def audit(root, run_host=False):
    root = pathlib.Path(root).resolve()
    checks = {p: {"exists": (root / p).is_file(), "purpose": why}
              for p, why in REQUIRED.items()}
    present = all(item["exists"] for item in checks.values())
    result = {
        "checks": checks,
        "prerequisites_present": present,
        "host_tests": "not_run",
        "capture_emulator_test_passed": False,
        "capture_emulator_test_status": "not_run",
        "capture_emulator_evidence": None,
        "note": "Host tests and screenshot-recognition tests cannot establish live emulator gameplay.",
    }
    if run_host:
        if not present:
            result["host_tests"] = "blocked_missing_prerequisites"
        else:
            try:
                proc = subprocess.run(
                    ["make", "test-host", "test-syntax"], cwd=root,
                    capture_output=True, text=True, timeout=300, check=False)
                result["host_tests"] = "passed" if proc.returncode == 0 else "failed"
                result["host_returncode"] = proc.returncode
                result["host_output_tail"] = (proc.stdout + proc.stderr)[-6000:]
            except (OSError, subprocess.TimeoutExpired) as exc:
                result["host_tests"] = "error"
                result["host_error"] = str(exc)
    return result

def _evidence_file(root, entry, suffix):
    """Verify a bundle-relative, hashed artifact without following paths outside root."""
    if not isinstance(entry, dict):
        return None
    name, digest = entry.get("path"), entry.get("sha256")
    if (not isinstance(name, str) or not name or
            pathlib.PurePosixPath(name).is_absolute() or
            "\\" in name or
            not isinstance(digest, str) or len(digest) != 64 or
            any(ch not in "0123456789abcdef" for ch in digest.lower())):
        return None
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.suffix.lower() != suffix or not candidate.is_file():
        return None
    # Avoid accidentally reading enormous or private dumps as screenshot evidence.
    if not 0 < candidate.stat().st_size <= 16 * 1024 * 1024:
        return None
    import hashlib
    data = candidate.read_bytes()
    if hashlib.sha256(data).hexdigest() != digest.lower():
        return None
    return data


def _valid_png(data):
    """Validate native-size screenshot pixels, not merely PNG chunk checksums.

    A well-formed IDAT chunk can still contain arbitrary bytes, a truncated
    deflate stream or a decompression bomb. Only complete non-interlaced PNG
    scanlines with valid filters are accepted as screenshot evidence.
    """
    import struct
    import zlib
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    pos = 8
    width = height = bit_depth = color_type = None
    image_data = bytearray()
    seen_idat = seen_end = seen_palette = False
    after_idat = False
    while pos + 12 <= len(data):
        length = struct.unpack_from(">I", data, pos)[0]
        if length > 16 * 1024 * 1024 or pos + 12 + length > len(data):
            return False
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc = struct.unpack_from(">I", data, pos + 8 + length)[0]
        if zlib.crc32(kind + body) & 0xffffffff != crc:
            return False
        pos += length + 12
        if width is None:
            if kind != b"IHDR" or length != 13:
                return False
            width, height, bit_depth, color_type, compression, filtering, interlace = (
                struct.unpack(">IIBBBBB", body))
            if (width != 256 or not 384 <= height <= 480 or
                    compression != 0 or filtering != 0 or interlace != 0):
                return False
            allowed_depths = {0: (1, 2, 4, 8, 16), 2: (8, 16),
                              3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if bit_depth not in allowed_depths.get(color_type, ()):
                return False
        elif kind == b"IHDR":
            return False
        elif kind == b"PLTE":
            if seen_idat or seen_palette or length == 0 or length % 3 or length > 768:
                return False
            seen_palette = True
        elif kind == b"IDAT":
            if after_idat or (color_type == 3 and not seen_palette):
                return False
            seen_idat = True
            image_data.extend(body)
            if len(image_data) > 16 * 1024 * 1024:
                return False
        elif kind == b"IEND":
            seen_end = length == 0 and pos == len(data)
            break
        elif seen_idat:
            after_idat = True
        # Unknown critical PNG chunks cannot be interpreted safely.
        if kind not in (b"IHDR", b"PLTE", b"IDAT", b"IEND") and kind[0] & 32 == 0:
            return False
    if not (seen_idat and seen_end):
        return False
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    row_bytes = (width * channels * bit_depth + 7) // 8
    expected = height * (row_bytes + 1)
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(bytes(image_data), expected + 1)
        if (len(raw) != expected or not decoder.eof or
                decoder.unused_data or decoder.unconsumed_tail or
                decoder.flush()):
            return False
    except zlib.error:
        return False
    if not all(raw[row * (row_bytes + 1)] <= 4 for row in range(height)):
        return None
    # Compare decoded scanlines rather than file hashes: PNG metadata and
    # zlib compression settings must not make one frame count as many.
    import hashlib
    return hashlib.sha256(struct.pack(">IIBB", width, height, bit_depth, color_type) +
                          raw).hexdigest()


def audit_emulator_evidence(root, evidence_dir):
    """Check artifact provenance/structure, not visual gameplay or retail parity."""
    evidence = pathlib.Path(evidence_dir).resolve()
    report = evidence / "capture-report.json"
    if not report.is_file():
        return {"status": "missing_report", "passed": False, "path": str(report)}
    try:
        payload = json.loads(report.read_text())
    except (OSError, ValueError) as exc:
        return {"status": "invalid_report", "passed": False, "error": str(exc)}
    required = ("cloud_search", "cloud_shot", "orb_collected",
                "sphere_encounter", "capture_reward", "results",
                "resume_radar", "save", "restart", "restored_reward")
    base = {"passed": False, "path": str(report),
            "required_stages": list(required),
            "note": "Artifact checks do not prove that a human verified gameplay in melonDS."}
    if (not isinstance(payload, dict) or payload.get("emulator") != "melonDS" or
            payload.get("test_kind") != "live_emulator_capture" or
            not isinstance(payload.get("stages"), dict) or
            not all(payload["stages"].get(s) is True for s in required)):
        return {**base, "status": "incomplete_stages"}
    import re
    if (not isinstance(payload.get("commit_sha"), str) or
            re.fullmatch(r"[0-9a-fA-F]{40}", payload["commit_sha"]) is None or
            not isinstance(payload.get("rom_sha256"), str) or
            re.fullmatch(r"[0-9a-fA-F]{64}", payload["rom_sha256"]) is None):
        return {**base, "status": "missing_build_identity"}
    log = _evidence_file(evidence, payload.get("runtime_log"), ".log")
    if not log or b"Emulator: melonDS" not in log or b"Window XID:" not in log:
        return {**base, "status": "invalid_emulator_log"}
    captures = payload.get("captures")
    if not isinstance(captures, dict):
        return {**base, "status": "missing_captures"}
    fingerprints = set()
    for stage in required:
        shot = captures.get(stage)
        data = _evidence_file(evidence, shot, ".png")
        if not data or not _valid_png(data):
            return {**base, "status": "invalid_capture", "failed_stage": stage}
        fingerprints.add(_valid_png(data))
    if len(fingerprints) < 4:
        return {**base, "status": "reused_captures"}
    return {**base, "status": "evidence_bundle_complete", "passed": True,
            "distinct_screenshots": len(fingerprints)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repository", nargs="?", default=".")
    parser.add_argument("--run-host", action="store_true",
                        help="Run make test-host test-syntax (up to 5 minutes)")
    parser.add_argument("--emulator-evidence", metavar="DIR",
                        help="Inspect a live emulator capture-report.json; navigation alone is insufficient")
    args = parser.parse_args()
    result = audit(args.repository, args.run_host)
    if args.emulator_evidence:
        evidence = audit_emulator_evidence(args.repository, args.emulator_evidence)
        result["capture_emulator_test_passed"] = evidence["passed"]
        result["capture_emulator_test_status"] = evidence["status"]
        result["capture_emulator_evidence"] = evidence
    print(json.dumps(result, indent=2))
    if not result["prerequisites_present"]:
        return 2
    if args.run_host and result["host_tests"] != "passed":
        return 1
    if args.emulator_evidence and not result["capture_emulator_test_passed"]:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
