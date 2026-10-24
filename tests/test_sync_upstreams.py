from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import sync_upstreams  # noqa: E402


class SyncUpstreamsTest(unittest.TestCase):
    def test_discovers_nested_skills_without_copying_nested_skill_files_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "skills"
            first = root / "group" / "first"
            nested = first / "reference"
            second = root / "second"
            nested.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "SKILL.md").write_text("---\nname: first\ndescription: first\n---\n")
            (nested / "SKILL.md").write_text("---\nname: nested\ndescription: nested\n---\n")
            (second / "SKILL.md").write_text("---\nname: second\ndescription: second\n---\n")
            self.assertEqual(["first", "second"], [p.name for p in sync_upstreams.skill_directories(root)])

    def test_rejects_duplicate_flattened_skill_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "skills"
            for group in ("one", "two"):
                skill = root / group / "duplicate"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text("---\nname: duplicate\ndescription: duplicate\n---\n")
            with self.assertRaises(sync_upstreams.SyncError):
                sync_upstreams.skill_directories(root)


if __name__ == "__main__":
    unittest.main()
