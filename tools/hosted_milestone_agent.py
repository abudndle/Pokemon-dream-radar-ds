#!/usr/bin/env python3
"""Fail-closed staged-change gate for the opt-in, GitHub-hosted coding agent.

This runs OUTSIDE the model sandbox, BEFORE publishing an automated draft PR.
The agent never gets write permission to workflows or proprietary asset paths.
"""
import argparse
import pathlib
import subprocess
import sys

ALLOWED_ROOTS = frozenset(("source", "tests", "tools", "docs", "scripts",
                           "companion", "public-demo", "include", "src"))
ALLOWED_ROOT_FILES = frozenset(("Makefile", "Makefile.native",
    "Makefile.devkitpro", "README.md", "DEVELOPMENT.md", "FEATURES.md"))
ALLOWED_SUFFIXES = frozenset((".c", ".h", ".py", ".sh", ".md", ".txt",
    ".json", ".toml", ".yaml", ".yml", ".mk", ".s", ".inc"))
FORBIDDEN_PARTS = frozenset(("private", "assets", "original_assets",
    "nitrofs", "romfs", "exefs", "sd-card", "build", "dist", "reference",
    "references", ".github", ".git", "__pycache__", ".env"))
PROTECTED_FILES = frozenset((
    "tools/hosted_milestone_agent.py",
    "tests/test_hosted_milestone_agent.py",
    "docs/HOSTED_MILESTONE_AGENT.md",
))
MAX_CHANGED_FILES = 25
MAX_CHANGED_BYTES = 400_000


def validate_paths(paths, root=pathlib.Path(".")):
    """Return a list of errors. No file may escape the checked-out workspace."""
    errors = []
    if len(paths) > MAX_CHANGED_FILES:
        errors.append("too many modified files")
    total = 0
    seen = set()
    for name in paths:
        posix = pathlib.PurePosixPath(name)
        parts = posix.parts
        if (not name or name in seen or name.startswith("/") or
                ".." in parts or "." in parts or "\\" in name):
            errors.append("invalid staged path: " + name)
            continue
        seen.add(name)
        if name in PROTECTED_FILES:
            errors.append("agent infrastructure cannot be edited: " + name)
        if any(part.lower() in FORBIDDEN_PARTS for part in parts):
            errors.append("private/asset/infrastructure path forbidden: " + name)
        if not parts or (len(parts) == 1 and name not in ALLOWED_ROOT_FILES):
            errors.append("unapproved root file: " + name)
        elif len(parts) > 1 and parts[0] not in ALLOWED_ROOTS:
            errors.append("unapproved source directory: " + name)
        if posix.suffix.lower() not in ALLOWED_SUFFIXES and name not in ALLOWED_ROOT_FILES:
            errors.append("non-source extension: " + name)
        file = root / name
        if file.is_symlink():
            errors.append("symlink forbidden: " + name)
        elif file.is_file():
            total += file.stat().st_size
        else:
            errors.append("deleted or missing staged file: " + name)
    if total > MAX_CHANGED_BYTES:
        errors.append("changes exceed maximum source size")
    return errors


def staged_paths():
    raw = subprocess.check_output(
        ["git", "diff", "--cached", "--name-only", "-z"])
    return [s.decode("utf-8", "strict") for s in raw.split(b"\0") if s]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check"])
    args = parser.parse_args()
    assert args.command == "check"
    paths = staged_paths()
    if not paths:
        print("No staged milestone changes")
        return 3
    errors = validate_paths(paths)
    if subprocess.run(["git", "diff", "--cached", "--check"]).returncode:
        errors.append("staged diff failed whitespace check")
    if errors:
        for error in errors:
            print("REJECTED: " + error, file=sys.stderr)
        return 2
    print("Agent source gate passed: %d files, only public source changes" % len(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
