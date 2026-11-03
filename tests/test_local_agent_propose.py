#!/usr/bin/env python3
"""Offline safety regression for untrusted local-model change proposals."""
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from local_agent_propose import validate_and_apply, c_tokens_without_comments, TASKS

# A comment must not count as changed C code, including multiline comments.
assert c_tokens_without_comments("int n=1; /* one\ntwo */ // tail\nreturn n;") == c_tokens_without_comments("int n = 1; return n;")
assert c_tokens_without_comments("int n=1;") != c_tokens_without_comments("int n=2;")
assert c_tokens_without_comments("int n=1; // old\nreturn n;") == c_tokens_without_comments("int n=1; // new\nreturn n;")

def change(path, old, new):
    return {"path": path, "old": old, "new": new}

with tempfile.TemporaryDirectory() as d:
    root = Path(d)
    paths = TASKS["cloud"][:2]
    for path in paths:
        (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / paths[0]).write_text("int sample(void) { return 1; }\n")
    (root / paths[1]).write_text("void verify(void) {\n    assert(1);\n}\n")
    proposal = {"summary": "Fix boundary error in the cloud frame sample", "changes": [
        change(paths[0], "return 1;", "return 2;"),
        change(paths[1], "assert(1);", "assert(2);"),
    ]}
    assert validate_and_apply(root, "cloud", proposal) == sorted(paths)
    assert "return 2;" in (root / paths[0]).read_text()
    assert "assert(2);" in (root / paths[1]).read_text()
    invalid = [
        {"summary": "Comment-only source edit is not implementation", "changes": [
            change(paths[0], "return 2;", "return 2; /* claimed fix */"),
            change(paths[1], "assert(2);", "assert(2);\n    assert(3);")]},
        {"summary": "Whitespace-only source edit is not implementation", "changes": [
            change(paths[0], "return 2;", "return   2;"),
            change(paths[1], "assert(2);", "assert(2);\n    assert(3);")]},
        {"summary": "Duplicate regression assertion", "changes": [
            change(paths[0], "return 2;", "return 3;"),
            change(paths[1], "assert(2);", "assert(2); assert(2);")]},
        {"summary": "Test-only changes", "changes": proposal["changes"][:1]},
        {"summary": "Workflow injection attempt", "changes": [
            change(".github/workflows/steal.yml", "a", "b"), proposal["changes"][1]]},
        {"summary": "Invented source snippet", "changes": [
            change(paths[0], "never existed", "x"), proposal["changes"][1]]},
        {"summary": "Duplicate source edit attempt", "changes": [
            change(paths[0], "return 2;", "return 2;"), proposal["changes"][1]]},
        {"summary": "Malformed proposal fields", "changes": [
            {"path": paths[0]}, proposal["changes"][1]]},
        {"summary": "Unsupported path traversal", "changes": [
            change("../README.md", "a", "b"), proposal["changes"][1]]},
    ]
    for bad in invalid:
        try:
            validate_and_apply(root, "cloud", bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsafe proposal accepted: " + bad["summary"])
    assert "return 2;" in (root / paths[0]).read_text()
    assert "assert(2);" in (root / paths[1]).read_text()

# Automatic runs cover every allowlisted module without expanding write permissions.
if "module" in globals():
    choose = module.select_focus
else:
    from local_agent_propose import select_focus as choose
keys = tuple(TASKS)
for index, key in enumerate(keys):
    # Each consecutive five-minute run must select the next supported module.
    assert choose("auto", index) == key
    assert choose("auto", index + len(keys)) == key
    assert choose(key, 0) == key
for invalid in ("not-a-module",):
    try:
        choose(invalid, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown module accepted")
try:
    choose("auto", -1)
except ValueError:
    pass
else:
    raise AssertionError("Negative rotation slot accepted")

print("PASS: local coding agent rejects untrusted, malformed and out-of-scope edits")
