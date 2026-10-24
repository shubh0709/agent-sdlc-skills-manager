#!/usr/bin/env python3
"""Check pinned upstreams and intentionally refresh one vendored collection."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "registry" / "sources.lock.json"


class SyncError(RuntimeError):
    pass


def run(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env={"PATH": os.environ.get("PATH", "")},
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SyncError(f"{' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def remote_head(source: dict) -> str:
    branch = source.get("branch", "main")
    output = run("git", "ls-remote", source["repository"], f"refs/heads/{branch}")
    if not output:
        raise SyncError(f"{source['id']}: branch {branch!r} was not found")
    return output.split()[0]


def choose_sources(data: dict, requested: list[str]) -> list[dict]:
    sources = data["sources"]
    known = {source["id"]: source for source in sources}
    missing = sorted(set(requested) - set(known))
    if missing:
        raise SyncError(f"unknown source(s): {', '.join(missing)}")
    return [known[item] for item in requested] if requested else sources


def skill_directories(root: Path) -> list[Path]:
    if not root.is_dir():
        raise SyncError(f"skill root does not exist: {root}")
    files = sorted(root.rglob("SKILL.md"))
    directories = []
    for file in files:
        parent = file.parent
        if any((ancestor / "SKILL.md").is_file() for ancestor in parent.parents if ancestor != root.parent):
            continue
        directories.append(parent)
    if not directories:
        raise SyncError(f"no SKILL.md files below {root}")
    names = [path.name for path in directories]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise SyncError(f"duplicate skill directory names: {', '.join(duplicates)}")
    return directories


def validate_skill(skill: Path) -> None:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\nname:" not in text or "\ndescription:" not in text:
        raise SyncError(f"invalid skill frontmatter: {skill / 'SKILL.md'}")


def safe_repo_path(value: str, required_parent: Path) -> Path:
    path = (ROOT / value).resolve()
    parent = required_parent.resolve()
    if path == parent or parent not in path.parents:
        raise SyncError(f"unsafe repository path in source lock: {value}")
    return path


def refresh(source: dict, temp_root: Path) -> tuple[str, int]:
    if source.get("sync_mode") != "vendored":
        raise SyncError(f"{source['id']} is reference-only and cannot be vendored")

    checkout = temp_root / f"checkout-{source['id']}"
    run(
        "git", "clone", "--quiet", "--depth", "1", "--branch",
        source.get("branch", "main"), source["repository"], str(checkout),
    )
    commit = run("git", "rev-parse", "HEAD", cwd=checkout)
    upstream_root = (checkout / source["skill_root"]).resolve()
    if checkout.resolve() not in upstream_root.parents:
        raise SyncError(f"{source['id']}: unsafe skill_root")

    candidate = temp_root / f"candidate-{source['id']}"
    candidate.mkdir()
    skills = skill_directories(upstream_root)
    for skill in skills:
        validate_skill(skill)
        shutil.copytree(skill, candidate / skill.name)

    target = safe_repo_path(source["target"], ROOT / "catalog")
    backup = temp_root / f"backup-{source['id']}"
    if target.exists():
        os.replace(target, backup)
    try:
        os.replace(candidate, target)
    except Exception:
        if backup.exists() and not target.exists():
            os.replace(backup, target)
        raise

    license_source = (checkout / source["license_source"]).resolve()
    if checkout.resolve() not in license_source.parents or not license_source.is_file():
        raise SyncError(f"{source['id']}: license file not found")
    license_target = safe_repo_path(source["license_file"], ROOT / "third_party")
    shutil.copy2(license_source, license_target)
    return commit, len(skills)


def write_lock(data: dict) -> None:
    fd, name = tempfile.mkstemp(prefix="sources-lock-", suffix=".json", dir=LOCK_PATH.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(name, LOCK_PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def command_check(args: argparse.Namespace) -> None:
    data = load_lock()
    rows = []
    for source in choose_sources(data, args.source):
        latest = remote_head(source)
        rows.append(
            {
                "id": source["id"],
                "mode": source.get("sync_mode", "reference"),
                "pinned": source["commit"],
                "latest": latest,
                "update_available": latest != source["commit"],
            }
        )
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            state = "UPDATE" if row["update_available"] else "current"
            print(f"{state:7} {row['id']:24} {row['pinned'][:12]} -> {row['latest'][:12]} ({row['mode']})")


def command_apply(args: argparse.Namespace) -> None:
    data = load_lock()
    selected = choose_sources(data, args.source)
    if not selected:
        raise SyncError("apply requires at least one --source")
    with tempfile.TemporaryDirectory(prefix=".upstream-sync-", dir=ROOT) as temp:
        temp_root = Path(temp)
        for source in selected:
            commit, count = refresh(source, temp_root)
            source["commit"] = commit
            print(f"refreshed {source['id']}: {count} skill(s) at {commit[:12]}")
    write_lock(data)
    run(sys.executable, str(ROOT / "scripts" / "rebuild_registry.py"), cwd=ROOT)
    run(sys.executable, str(ROOT / "scripts" / "skillctl.py"), "doctor", cwd=ROOT)
    print("Review the diff, upstream license, instructions, and executable files; then run the test suite.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="compare pins with upstream branch heads")
    check.add_argument("--source", action="append", default=[])
    check.add_argument("--json", action="store_true")
    check.set_defaults(func=command_check)
    apply = commands.add_parser("apply", help="replace one reviewed vendored source")
    apply.add_argument("--source", action="append", required=True)
    apply.set_defaults(func=command_apply)
    return result


def main() -> None:
    args = parser().parse_args()
    try:
        args.func(args)
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
