from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RALPH = ROOT / "skills" / "ralph-loop" / "scripts" / "ralph.py"

spec = importlib.util.spec_from_file_location("ralph", RALPH)
assert spec and spec.loader
ralph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ralph)


class RalphTest(unittest.TestCase):
    def run_ralph(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RALPH), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_selects_priority_ticket_with_satisfied_dependencies(self) -> None:
        tickets = [
            {"id": "B", "priority": 1, "status": "pending", "depends_on": ["A"]},
            {"id": "C", "priority": 5, "status": "pending", "depends_on": []},
            {"id": "A", "priority": 10, "status": "done", "verification_evidence": ["ok"]},
        ]
        self.assertEqual("B", ralph.ready_ticket(tickets)["id"])

    def test_rejects_multiple_terminal_signals(self) -> None:
        with self.assertRaises(ralph.RalphError):
            ralph.parse_signal(
                "<promise>TICKET-1:DONE</promise> <promise>COMPLETE</promise>"
            )

    def test_runs_fresh_process_per_ticket_and_completes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            initialized = self.run_ralph("init", "--project", str(project))
            self.assertEqual(0, initialized.returncode, initialized.stderr)
            tickets_path = project / ".sdlc" / "tickets.json"
            tickets_path.write_text(
                json.dumps(
                    {
                        "tickets": [
                            {"id": "TICKET-1", "priority": 1, "status": "pending", "depends_on": []},
                            {"id": "TICKET-2", "priority": 2, "status": "pending", "depends_on": ["TICKET-1"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            fake = project / "fake_agent.py"
            fake.write_text(
                """import json, os
from pathlib import Path
root = Path(os.environ['RALPH_PROJECT_ROOT'])
path = root / '.sdlc' / 'tickets.json'
data = json.loads(path.read_text())
ticket_id = os.environ['RALPH_TICKET_ID']
for ticket in data['tickets']:
    if ticket['id'] == ticket_id:
        ticket['status'] = 'done'
        ticket['verification_evidence'] = ['fake test passed']
path.write_text(json.dumps(data, indent=2) + '\\n')
print(f'<promise>{ticket_id}:DONE</promise>')
""",
                encoding="utf-8",
            )
            config_path = project / ".sdlc" / "ralph" / "config.json"
            config = json.loads(config_path.read_text())
            config["agent_command"] = [sys.executable, str(fake), "{prompt_file}"]
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = self.run_ralph(
                "run", "--project", str(project), "--allow-dirty", "--max-iterations", "3"
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            tickets = json.loads(tickets_path.read_text())["tickets"]
            self.assertTrue(all(ticket["status"] == "done" for ticket in tickets))
            state = json.loads((project / ".sdlc" / "run-state.json").read_text())
            self.assertEqual("complete", state["status"])
            self.assertEqual(["TICKET-1", "TICKET-2"], state["completed_tickets"])
            histories = list((project / ".sdlc" / "ralph" / "history").glob("*.txt"))
            self.assertEqual(2, len(histories))

    def test_stops_after_repeated_identical_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            self.assertEqual(0, self.run_ralph("init", "--project", str(project)).returncode)
            (project / ".sdlc" / "tickets.json").write_text(
                json.dumps({"tickets": [{"id": "TICKET-1", "status": "pending"}]}),
                encoding="utf-8",
            )
            fake = project / "fail.py"
            fake.write_text("print('same deterministic failure')\n", encoding="utf-8")
            config_path = project / ".sdlc" / "ralph" / "config.json"
            config = json.loads(config_path.read_text())
            config["agent_command"] = [sys.executable, str(fake), "{prompt_file}"]
            config_path.write_text(json.dumps(config), encoding="utf-8")

            result = self.run_ralph(
                "run", "--project", str(project), "--allow-dirty",
                "--max-iterations", "4", "--max-same-failure", "2",
            )
            self.assertEqual(2, result.returncode, result.stderr + result.stdout)
            state = json.loads((project / ".sdlc" / "run-state.json").read_text())
            self.assertEqual("blocked", state["status"])
            self.assertEqual(2, state["ralph"]["same_failure_count"])


if __name__ == "__main__":
    unittest.main()
