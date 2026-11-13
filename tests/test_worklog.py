from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "worklog.py"


class WorklogTest(unittest.TestCase):
    def run_cli(self, project: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(CLI), "--project", str(project), *args],
            capture_output=True, text=True, check=False,
        )

    def test_records_and_builds_offline_dashboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            init = self.run_cli(project, "init")
            self.assertEqual(init.returncode, 0, init.stderr)
            source = project / "design.md"
            source.write_text(
                "Approach A vs B\n\n```python\nprint('<script>alert(1)</script>')\n```\n", encoding="utf-8"
            )
            one = self.run_cli(project, "record", "--section", "hld", "--title", "Design choices",
                               "--body-file", str(source), "--status", "proposed")
            self.assertEqual(one.returncode, 0, one.stderr)
            events = list((project / ".worklog" / "events").glob("*.json"))
            self.assertEqual(len(events), 1)
            previous = json.loads(events[0].read_text())
            two = self.run_cli(project, "record", "--section", "decisions", "--title", "Chosen approach",
                               "--body", "Explicitly approved by the user", "--status", "approved",
                               "--supersedes", previous["id"])
            self.assertEqual(two.returncode, 0, two.stderr)
            result = self.run_cli(project, "render")
            self.assertEqual(result.returncode, 0, result.stderr)
            page = (project / ".worklog" / "index.html").read_text()
            self.assertIn("Design choices", page)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
            self.assertNotIn("<script>alert(1)</script>", page)
            self.assertIn("<pre><code", page)
            self.assertIn("white-space:pre-wrap", page)
            self.assertIn("supersedes", page)
            self.assertIn("Chosen approach", (project / ".worklog" / "work-log.md").read_text())
            self.assertIn("Design choices", (project / ".worklog" / "hld.md").read_text())

    def test_invalid_supersession_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            result = self.run_cli(project, "record", "--section", "lld", "--title", "Something",
                                  "--body", "Test", "--supersedes", "nonexistent")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(len(list((project / ".worklog" / "events").glob("*.json"))), 0)


if __name__ == "__main__":
    unittest.main()
