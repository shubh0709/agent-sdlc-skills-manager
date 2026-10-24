#!/usr/bin/env python3
"""Rebuild compact skill routing metadata from vendored SKILL.md files."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry"

STAGE_TERMS = {
    "clarify": ("interview", "grill", "idea", "questionnaire", "premise", "domain model", "requirements"),
    "specify": ("spec", "requirements", "acceptance criteria", "proposal", "prd", "documentation", "adr"),
    "ticket": ("ticket", "task breakdown", "planning", "plan", "triage", "handoff"),
    "design": ("design", "architecture", "api", "interface", "domain", "data model", "prototype"),
    "implement": ("implement", "code", "typescript", "frontend", "refactor", "migration", "scaffold", "library"),
    "test": ("test", "browser", "playwright", "debug", "diagnos", "performance", "accessibility", "devtools"),
    "review": ("review", "quality", "blast radius", "security", "simplif", "doubt", "audit"),
    "verify": ("verif", "prove", "evidence", "validate", "check", "observability"),
    "ship": ("ship", "launch", "deploy", "ci/cd", "release", "git", "version", "rollback"),
    "operate": ("monitor", "observability", "incident", "production", "recovery", "maintain"),
}


def yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return json.loads(value)
    if len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return value


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not match:
        raise ValueError(f"missing YAML frontmatter: {path}")
    lines = match.group(1).splitlines()
    data: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        field = re.match(r"^(name|description):\s*(.*)$", line)
        if not field:
            index += 1
            continue
        key, value = field.groups()
        if value in {">", ">-", "|", "|-"}:
            folded: list[str] = []
            index += 1
            while index < len(lines) and (not lines[index].strip() or lines[index][:1].isspace()):
                folded.append(lines[index].strip())
                index += 1
            data[key] = " ".join(part for part in folded if part)
            continue
        data[key] = yaml_scalar(value)
        index += 1
    if not data.get("name") or not data.get("description"):
        raise ValueError(f"missing name or description: {path}")
    return data


def load_core() -> set[str]:
    data = json.loads((ROOT / "profiles" / "core.json").read_text(encoding="utf-8"))
    return set(data["skills"])


def stages_for(name: str, description: str) -> list[str]:
    haystack = f"{name} {description}".lower().replace("-", " ")
    stages = [stage for stage, terms in STAGE_TERMS.items() if any(term in haystack for term in terms)]
    return stages or ["implement"]


def discover() -> list[dict]:
    core = load_core()
    records: list[dict] = []
    roots = [("local", ROOT / "skills")]
    roots.extend((p.name, p) for p in sorted((ROOT / "catalog").iterdir()) if p.is_dir())

    for source, source_root in roots:
        for skill_file in sorted(source_root.glob("*/SKILL.md")):
            data = frontmatter(skill_file)
            name = str(data["name"])
            description = " ".join(str(data["description"]).split())
            skill_id = f"{source}/{name}"
            records.append(
                {
                    "id": skill_id,
                    "name": name,
                    "source": source,
                    "description": description,
                    "stages": stages_for(name, description),
                    "path": skill_file.parent.relative_to(ROOT).as_posix(),
                    "core": skill_id in core,
                }
            )
    return sorted(records, key=lambda row: row["id"])


def main() -> None:
    records = discover()
    REGISTRY.mkdir(parents=True, exist_ok=True)
    (REGISTRY / "skills.json").write_text(
        json.dumps({"schema_version": 1, "skills": records}, indent=2) + "\n",
        encoding="utf-8",
    )

    stages_dir = REGISTRY / "stages"
    stages_dir.mkdir(parents=True, exist_ok=True)
    for stage in STAGE_TERMS:
        selected = [row["id"] for row in records if stage in row["stages"]]
        (stages_dir / f"{stage}.json").write_text(
            json.dumps({"stage": stage, "skills": selected}, indent=2) + "\n",
            encoding="utf-8",
        )
    print(f"Wrote {len(records)} records ({sum(r['core'] for r in records)} core).")


if __name__ == "__main__":
    main()

