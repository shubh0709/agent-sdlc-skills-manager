#!/usr/bin/env python3
"""Install a small, managed selection from the local skill catalog."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "skills.json"
ADAPTERS_PATH = ROOT / "registry" / "adapters.json"
STATE_FILE = ".agent-skills-state.json"
MARKER_FILE = ".skillctl.json"


class SkillCtlError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SkillCtlError(f"cannot read {path}: {exc}") from exc


def registry() -> dict[str, dict]:
    if not REGISTRY_PATH.exists():
        raise SkillCtlError("registry missing; run python scripts/rebuild_registry.py")
    return {row["id"]: row for row in load_json(REGISTRY_PATH)["skills"]}


def destination(args: argparse.Namespace) -> Path:
    if getattr(args, "target", None):
        return Path(args.target).expanduser().resolve()
    adapters = load_json(ADAPTERS_PATH)
    editor = getattr(args, "editor", "agents")
    if editor not in adapters:
        raise SkillCtlError(f"unknown editor {editor!r}; choose: {', '.join(sorted(adapters))}")
    project = Path(getattr(args, "project", ".")).expanduser().resolve()
    return project / adapters[editor]


def state_path(dest: Path) -> Path:
    return dest.parent / STATE_FILE


def load_state(dest: Path) -> dict:
    path = state_path(dest)
    if not path.exists():
        return {"schema_version": 1, "destination": str(dest), "managed": {}}
    state = load_json(path)
    if Path(state.get("destination", "")).resolve() != dest.resolve():
        raise SkillCtlError(f"state file belongs to another destination: {path}")
    return state


def write_state(dest: Path, state: dict, dry_run: bool) -> None:
    if dry_run:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    state_path(dest).write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def resolve_skill(skill_id: str, records: dict[str, dict]) -> tuple[dict, Path]:
    if skill_id not in records:
        matches = [row for key, row in records.items() if row["name"] == skill_id]
        if len(matches) == 1:
            row = matches[0]
        elif len(matches) > 1:
            raise SkillCtlError(f"ambiguous skill name {skill_id!r}; use source/name")
        else:
            raise SkillCtlError(f"unknown skill {skill_id!r}; use search or list")
    else:
        row = records[skill_id]
    source = (ROOT / row["path"]).resolve()
    if ROOT not in source.parents or not (source / "SKILL.md").is_file():
        raise SkillCtlError(f"invalid source path for {row['id']}")
    return row, source


def install_one(skill_id: str, dest: Path, state: dict, dry_run: bool) -> None:
    records = registry()
    row, source = resolve_skill(skill_id, records)
    target = (dest / row["name"]).resolve()
    if dest.resolve() not in target.parents:
        raise SkillCtlError("refusing path outside destination")

    existing_owner = state["managed"].get(row["name"])
    if target.exists() and existing_owner not in (None, row["id"]):
        raise SkillCtlError(f"{target} is managed by {existing_owner}")
    if target.exists() and existing_owner is None:
        raise SkillCtlError(f"refusing to overwrite unmanaged directory: {target}")
    if target.exists() and existing_owner == row["id"]:
        marker = target / MARKER_FILE
        marker_data = load_json(marker) if marker.is_file() else {}
        if marker_data.get("id") != row["id"]:
            raise SkillCtlError(f"refusing to overwrite unverified managed directory: {target}")

    print(f"{'Would enable' if dry_run else 'Enabling'} {row['id']} -> {target}")
    if not dry_run:
        dest.mkdir(parents=True, exist_ok=True)
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        (target / MARKER_FILE).write_text(
            json.dumps({"id": row["id"], "source_path": row["path"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        state["managed"][row["name"]] = row["id"]
        if row["id"] == "local/sdlc-orchestrator":
            context = {
                "skill_repo": str(ROOT),
                "skillctl": str(ROOT / "scripts" / "skillctl.py"),
                "registry": str(REGISTRY_PATH),
                "destination": str(dest),
            }
            ref = target / "references" / "install-context.json"
            ref.parent.mkdir(parents=True, exist_ok=True)
            ref.write_text(json.dumps(context, indent=2) + "\n", encoding="utf-8")


def remove_one(name_or_id: str, dest: Path, state: dict, dry_run: bool) -> None:
    managed = state["managed"]
    names = [name for name, skill_id in managed.items() if name == name_or_id or skill_id == name_or_id]
    if not names:
        raise SkillCtlError(f"{name_or_id!r} is not managed in {dest}")
    for name in names:
        target = (dest / name).resolve()
        if dest.resolve() not in target.parents:
            raise SkillCtlError("refusing path outside destination")
        print(f"{'Would disable' if dry_run else 'Disabling'} {managed[name]} from {target}")
        if not dry_run:
            if target.exists():
                marker = target / MARKER_FILE
                marker_data = load_json(marker) if marker.is_file() else {}
                if marker_data.get("id") != managed[name]:
                    raise SkillCtlError(f"refusing to remove unverified managed directory: {target}")
                shutil.rmtree(target)
            del managed[name]


def profile_ids(name: str) -> list[str]:
    path = ROOT / "profiles" / f"{name}.json"
    if not path.is_file():
        choices = ", ".join(p.stem for p in sorted((ROOT / "profiles").glob("*.json")))
        raise SkillCtlError(f"unknown profile {name!r}; choose: {choices}")
    return load_json(path)["skills"]


def cmd_apply(args: argparse.Namespace) -> None:
    dest = destination(args)
    state = load_state(dest)
    wanted = profile_ids(args.profile)
    records = registry()
    wanted_names = {resolve_skill(skill_id, records)[0]["name"] for skill_id in wanted}
    for name in sorted(set(state["managed"]) - wanted_names):
        remove_one(name, dest, state, args.dry_run)
    for skill_id in wanted:
        install_one(skill_id, dest, state, args.dry_run)
    write_state(dest, state, args.dry_run)


def cmd_enable(args: argparse.Namespace) -> None:
    dest = destination(args)
    state = load_state(dest)
    install_one(args.skill, dest, state, args.dry_run)
    write_state(dest, state, args.dry_run)


def cmd_disable(args: argparse.Namespace) -> None:
    dest = destination(args)
    state = load_state(dest)
    remove_one(args.skill, dest, state, args.dry_run)
    write_state(dest, state, args.dry_run)


def cmd_status(args: argparse.Namespace) -> None:
    dest = destination(args)
    state = load_state(dest)
    print(f"Destination: {dest}")
    if not state["managed"]:
        print("No managed skills.")
    for name, skill_id in sorted(state["managed"].items()):
        marker = "ok" if (dest / name / "SKILL.md").is_file() else "missing"
        print(f"{marker:7} {skill_id}")


def cmd_search(args: argparse.Namespace) -> None:
    terms = [term.lower() for term in args.query]
    rows = []
    for row in registry().values():
        haystack = " ".join([row["id"], row["description"], *row["stages"]]).lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            rows.append((score, row))
    for _, row in sorted(rows, key=lambda item: (-item[0], not item[1]["core"], item[1]["id"]))[: args.limit]:
        core = " [core]" if row["core"] else ""
        print(f"{row['id']}{core}\n  stages: {', '.join(row['stages'])}\n  {row['description']}")


def cmd_list(args: argparse.Namespace) -> None:
    rows = registry().values()
    if args.stage:
        rows = [row for row in rows if args.stage in row["stages"]]
    if args.core:
        rows = [row for row in rows if row["core"]]
    for row in sorted(rows, key=lambda item: item["id"]):
        print(f"{row['id']}\t{','.join(row['stages'])}\t{row['description']}")


def cmd_doctor(_: argparse.Namespace) -> None:
    records = registry()
    errors = []
    names = {}
    for skill_id, row in records.items():
        path = ROOT / row["path"] / "SKILL.md"
        if not path.is_file():
            errors.append(f"missing {path}")
        names.setdefault(row["name"], []).append(skill_id)
    for profile in sorted((ROOT / "profiles").glob("*.json")):
        for skill_id in load_json(profile)["skills"]:
            if skill_id not in records:
                errors.append(f"{profile.name}: unknown {skill_id}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SkillCtlError(f"doctor found {len(errors)} problem(s)")
    collisions = {name: ids for name, ids in names.items() if len(ids) > 1}
    print(f"OK: {len(records)} skills, {sum(r['core'] for r in records.values())} core, {len(collisions)} cross-source name collisions.")


def add_destination_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--editor", default="agents", choices=sorted(load_json(ADAPTERS_PATH)))
    parser.add_argument("--project", default=".")
    parser.add_argument("--target", help="Explicit skill directory; overrides --editor and --project")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)

    apply = sub.add_parser("apply", help="Reconcile managed skills to a profile")
    apply.add_argument("profile")
    add_destination_flags(apply)
    apply.add_argument("--dry-run", action="store_true")
    apply.set_defaults(func=cmd_apply)

    enable = sub.add_parser("enable", help="Enable one catalog skill")
    enable.add_argument("skill")
    add_destination_flags(enable)
    enable.add_argument("--dry-run", action="store_true")
    enable.set_defaults(func=cmd_enable)

    disable = sub.add_parser("disable", help="Disable one managed skill")
    disable.add_argument("skill")
    add_destination_flags(disable)
    disable.add_argument("--dry-run", action="store_true")
    disable.set_defaults(func=cmd_disable)

    status = sub.add_parser("status", help="Show managed skills")
    add_destination_flags(status)
    status.set_defaults(func=cmd_status)

    search = sub.add_parser("search", help="Search names, descriptions, and stages")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int, default=12)
    search.set_defaults(func=cmd_search)

    listing = sub.add_parser("list", help="List catalog entries")
    listing.add_argument("--stage")
    listing.add_argument("--core", action="store_true")
    listing.set_defaults(func=cmd_list)

    doctor = sub.add_parser("doctor", help="Validate registry paths and profiles")
    doctor.set_defaults(func=cmd_doctor)
    return result


def main() -> int:
    try:
        args = parser().parse_args()
        args.func(args)
        return 0
    except SkillCtlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

