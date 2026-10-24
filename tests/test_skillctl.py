from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "skillctl.py"


class SkillCtlTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_registry_has_121_upstream_and_two_local_skills(self) -> None:
        data = json.loads((ROOT / "registry" / "skills.json").read_text())
        upstream = [row for row in data["skills"] if row["source"] != "local"]
        local = [row for row in data["skills"] if row["source"] == "local"]
        self.assertEqual(121, len(upstream))
        self.assertEqual({"sdlc-orchestrator", "ralph-loop"}, {row["name"] for row in local})

    def test_core_materializes_18_skills_and_reset_removes_optional(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            first = self.run_cli("apply", "core", "--project", str(project))
            self.assertEqual(0, first.returncode, first.stderr)
            skill_dir = project / ".agents" / "skills"
            self.assertEqual(18, len(list(skill_dir.glob("*/SKILL.md"))))

            enabled = self.run_cli(
                "enable",
                "addy-osmani/security-and-hardening",
                "--project",
                str(project),
            )
            self.assertEqual(0, enabled.returncode, enabled.stderr)
            self.assertTrue((skill_dir / "security-and-hardening" / "SKILL.md").is_file())

            reset = self.run_cli("apply", "core", "--project", str(project))
            self.assertEqual(0, reset.returncode, reset.stderr)
            self.assertFalse((skill_dir / "security-and-hardening").exists())

    def test_refuses_to_overwrite_unmanaged_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / ".agents" / "skills" / "tdd"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("mine", encoding="utf-8")
            result = self.run_cli("apply", "core", "--project", temp)
            self.assertEqual(2, result.returncode)
            self.assertIn("refusing to overwrite unmanaged", result.stderr)


if __name__ == "__main__":
    unittest.main()
