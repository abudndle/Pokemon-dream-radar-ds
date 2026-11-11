#!/usr/bin/env python3
"""Constrained local-Ollama code proposal generator; never executes model commands."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

TASKS = {
    "platform": (
        "source/platform_compat.c", "tests/test_platform_compat.c",
        "Fix a concrete correctness or safety bug in DS/DSi input or storage. "
        "Preserve public API and add a regression assertion."),
    "album": (
        "source/photo_album.c", "tests/test_photo_album.c",
        "Fix a concrete correctness or safety bug in photo storage or parsing. "
        "Preserve public API and add a regression assertion."),
    "cloud": (
        "source/cloud_animation.c", "tests/test_cloud_animation.c",
        "Fix a concrete correctness or boundary bug in cloud animation. "
        "Preserve public API and add a regression assertion."),
}

# Exact existing milestone issue mapping. No issue-title text or user-supplied
# GitHub content enters the model instructions or the privileged publisher.
MILESTONE_ISSUES = {
    "platform": 64,  # DS renderer, controls and DSi camera
    "album": 65,     # Save, resume and storage compatibility
    "cloud": 63,     # Radar gameplay, cloud and encounter logic
}
assert set(MILESTONE_ISSUES) == set(TASKS)

def c_tokens_without_comments(value: str) -> list[str]:
    """Ignore comments and whitespace when comparing C implementation."""
    value = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", value)
    return re.findall(r"[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]", value)


def validate_and_apply(root: Path, focus: str, plan: dict) -> list[str]:
    """Permit only short exact-snippet edits to an existing source/test pair."""
    if focus not in TASKS or not isinstance(plan, dict):
        raise ValueError("Unknown focus or malformed proposal")
    summary = plan.get("summary")
    changes = plan.get("changes")
    if not isinstance(summary, str) or not 8 <= len(summary.strip()) <= 120:
        raise ValueError("Short specific summary required")
    if not isinstance(changes, list) or not 2 <= len(changes) <= 4:
        raise ValueError("Expected 2 to 4 exact-snippet edits")
    allowed = set(TASKS[focus][:2])
    updated = {}
    for c in changes:
        if not isinstance(c, dict) or set(c) != {"path", "old", "new"}:
            raise ValueError("Only path, old and new are allowed")
        path, old, new = c["path"], c["old"], c["new"]
        if type(path) is not str or path not in allowed:
            raise ValueError("Forbidden path")
        if (type(old) is not str or type(new) is not str or
            not 1 <= len(old) <= 1800 or not 1 <= len(new) <= 2400 or old == new):
            raise ValueError("Edit is empty, oversized or a no-op")
        target = root / path
        if not target.is_file() or target.is_symlink():
            raise ValueError("Target missing or symlinked")
        before = updated.get(path, target.read_text(encoding="utf-8"))
        if before.count(old) != 1:
            raise ValueError("Original snippet must occur exactly once")
        updated[path] = before.replace(old, new, 1)
    if set(updated) != allowed:
        raise ValueError("Both the source and its regression test must change")
    source_path, test_path = TASKS[focus][:2]
    if c_tokens_without_comments((root / source_path).read_text(encoding="utf-8")) == c_tokens_without_comments(updated[source_path]):
        raise ValueError("No semantic source change (comments/whitespace only)")

    # The model must add a genuinely new regression, not repeat an assertion
    # already present in the original test (a past agent false positive).
    pattern = r"(?m)^[ \t]*assert\s*\([^;\n]*\)\s*;[ \t]*(?://[^\n]*)?$"
    before_asserts = set(re.findall(pattern, (root / test_path).read_text(encoding="utf-8")))
    after_asserts = set(re.findall(pattern, updated[test_path]))
    if not after_asserts - before_asserts:
        raise ValueError("No new distinct regression assertion")
    for path, value in updated.items():
        original = (root / path).read_text(encoding="utf-8")
        if len(value) > len(original) + 2800 or len(value) < len(original) - 1800:
            raise ValueError("Whole-file rewrites are not allowed")
    for path, value in updated.items():
        (root / path).write_text(value, encoding="utf-8")
    return sorted(updated)

def generate_plan(root: Path, focus: str, model: str, endpoint: str) -> dict:
    source, test, goal = TASKS[focus]
    if endpoint != "http://127.0.0.1:11434/api/generate":
        raise ValueError("Only locally served Ollama is allowed")
    contract = (root / "AGENTS.md").read_text(encoding="utf-8")[:6500]
    prompt = (
        "PROJECT COMPATIBILITY CONTRACT (requirements, not executable instructions):\\n"
        + contract + "\\n"
        "Act as a cautious C developer. Find a real reproducible defect, fix it "
        "with one or two tiny changes, and add a regression assertion. "
        "If no defect exists, return an empty changes list. "
        "Copy each old snippet byte-for-byte from the provided file, including whitespace, indentation and punctuation; never paraphrase. Use a short contiguous snippet that appears exactly once. Place each new C assert statement on its own line (not after another statement), and test the specific changed behavior rather than adding a tautology. "
        "Reply with ONE JSON object, never markdown or shell commands. "
        "Schema: {\"summary\":\"specific defect\", \"changes\": "
        "[{\"path\":\"source file\",\"old\":\"exact verbatim snippet\","
        "\"new\":\"replacement\"},{\"path\":\"test file\","
        "\"old\":\"exact verbatim snippet\",\"new\":\"replacement with assertion\"}]}. "
        "Do not modify file paths, build scripts, workflows, networking or assets. "
        "Preserve all existing APIs and tests. Work toward existing milestone "
        + str(MILESTONE_ISSUES[focus]) + " using this source/test pair only. Task: " + goal + "\n"
        + "SOURCE [" + source + "]:\n" + (root/source).read_text(encoding="utf-8")
        + "\nTEST [" + test + "]:\n" + (root/test).read_text(encoding="utf-8")
    )
    body = {"model": model, "prompt": prompt, "format": "json", "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1800, "num_ctx": 8192}}
    request = urllib.request.Request(endpoint, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.load(response)
    if type(result) is not dict or type(result.get("response")) is not str:
        raise ValueError("Malformed local model response")
    return json.loads(result["response"])

def run(root: Path, output_dir: Path, focus: str, model: str, endpoint: str,
        plan_file: Path | None = None, *, validate=True) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    if focus not in TASKS:
        raise ValueError("Invalid focus")
    original = {path: (root / path).read_bytes() for path in TASKS[focus][:2]}
    last_error = None
    # Keep retries independent: restore both files after each rejected candidate.
    for attempt in range(2 if plan_file is None else 1):
        try:
            plan = (json.loads(plan_file.read_text(encoding="utf-8"))
                    if plan_file else generate_plan(root, focus, model, endpoint))
            paths = validate_and_apply(root, focus, plan)
            if validate:
                subprocess.run(["make", "test-host", "test-syntax"], cwd=root,
                               check=True, timeout=420)
                subprocess.run(["git", "diff", "--check"], cwd=root,
                               check=True, timeout=20)
            patch = subprocess.run(["git", "diff", "--", *paths], cwd=root,
                                   check=True, capture_output=True, text=True,
                                   timeout=20).stdout
            if not patch or len(patch) > 14000:
                raise ValueError("No bounded code patch produced")
            (output_dir / "proposal.patch").write_text(patch, encoding="utf-8")
            (output_dir / "proposal.json").write_text(json.dumps({
                "summary": plan["summary"], "focus": focus,
                "milestone_issue": MILESTONE_ISSUES[focus], "paths": paths,
                "model": model, "validated": bool(validate)}, indent=2) + "\n",
                encoding="utf-8")
            return True
        except (ValueError, OSError, TimeoutError, json.JSONDecodeError,
                subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            for path, data in original.items():
                (root / path).write_bytes(data)
            print(f"Rejected candidate {attempt + 1}: {exc}", file=sys.stderr)
    raise ValueError("No passing proposal: " + str(last_error))

def select_focus(requested: str, run_slot: int) -> str:
    """Rotate allowed modules on each five-minute CI interval."""
    if requested != "auto":
        if requested not in TASKS:
            raise ValueError("Unknown focus")
        return requested
    if run_slot < 0:
        raise ValueError("Negative run slot")
    keys = tuple(TASKS)
    return keys[run_slot % len(keys)]

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--focus", choices=[*TASKS, "auto"], default="auto")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-dir", type=Path, default=Path("agent-output"))
    parser.add_argument("--model", default=os.getenv("LOCAL_AGENT_MODEL", "qwen2.5-coder:1.5b"))
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    args = parser.parse_args()
    if args.focus == "auto":
        from datetime import datetime, timezone
        args.focus = select_focus("auto", int(datetime.now(timezone.utc).timestamp() // 300))
        print(f"Autonomous module focus: {args.focus}")
    try:
        run(args.root, args.output_dir, args.focus, args.model, args.endpoint)
    except (ValueError, OSError, TimeoutError, json.JSONDecodeError,
            subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print("No safe validated proposal produced: " + str(exc), file=sys.stderr)
        return 1
    print("Validated source/test patch produced for draft review PR")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
