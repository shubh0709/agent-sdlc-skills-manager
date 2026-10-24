#!/usr/bin/env python3
"""Bounded, resumable, one-ticket-per-process Ralph loop controller."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXIT_COMPLETE = 0
EXIT_BUDGET = 1
EXIT_BLOCKED = 2
EXIT_DECIDE = 3
EXIT_ERROR = 4

SIGNAL_RE = re.compile(
    r"<promise>(COMPLETE|STEERING:DONE|BLOCKED:[^<]+|DECIDE:[^<]+|"
    r"[A-Za-z0-9._-]+:DONE)</promise>"
)


class RalphError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RalphError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RalphError(f"expected a JSON object in {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_once(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def paths(project: Path) -> dict[str, Path]:
    root = project / ".sdlc"
    ralph = root / "ralph"
    return {
        "root": root,
        "config": ralph / "config.json",
        "tickets": root / "tickets.json",
        "state": root / "run-state.json",
        "spec": root / "spec.md",
        "steering": root / "steering.md",
        "prompt": ralph / "current-prompt.md",
        "log": ralph / "log.md",
        "history": ralph / "history",
        "ignore": root / ".gitignore",
    }


def default_state() -> dict[str, Any]:
    return {
        "feature": "",
        "stage": "implement",
        "status": "paused",
        "current_ticket": None,
        "completed_tickets": [],
        "failed_attempts": [],
        "last_verified_commit": None,
        "next_action": "Review the specification and tickets, then start Ralph.",
        "blockers": [],
        "activated_skills": ["sdlc-orchestrator", "ralph-loop"],
        "ralph": {"iteration": 0, "started_at": None, "updated_at": now()},
    }


def init_project(project: Path) -> None:
    p = paths(project)
    created = []
    files = {
        p["config"]: json.dumps(
            {
                "agent_command": [],
                "max_iterations": 10,
                "max_minutes": 120,
                "iteration_timeout_seconds": 1800,
                "max_same_failure": 3,
                "allow_commit": False,
                "require_clean_worktree": True,
            },
            indent=2,
        )
        + "\n",
        p["tickets"]: '{\n  "tickets": []\n}\n',
        p["state"]: json.dumps(default_state(), indent=2) + "\n",
        p["steering"]: "# Live steering\n\n<!-- Put urgent instructions here; remove them when resolved. -->\n",
        p["log"]: "# Ralph progress\n",
        p["ignore"]: (
            "run-state.json\nsteering.md\nralph/current-prompt.md\n"
            "ralph/log.md\nralph/history/\n"
        ),
    }
    for path, content in files.items():
        if write_once(path, content):
            created.append(path.relative_to(project).as_posix())
    p["history"].mkdir(parents=True, exist_ok=True)
    print("Created: " + (", ".join(created) if created else "nothing; existing files preserved"))


def ticket_list(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    tickets = data.get("tickets")
    if not isinstance(tickets, list):
        raise RalphError(f"{path} must contain a tickets array")
    ids: set[str] = set()
    for ticket in tickets:
        if not isinstance(ticket, dict) or not isinstance(ticket.get("id"), str):
            raise RalphError("every ticket must be an object with a string id")
        if ticket["id"] in ids:
            raise RalphError(f"duplicate ticket id: {ticket['id']}")
        ids.add(ticket["id"])
    return tickets


def is_done(ticket: dict[str, Any]) -> bool:
    return ticket.get("status") == "done" or ticket.get("passes") is True


def has_evidence(ticket: dict[str, Any]) -> bool:
    evidence = ticket.get("verification_evidence")
    return bool(evidence) and isinstance(evidence, (str, list, dict))


def ready_ticket(tickets: list[dict[str, Any]]) -> dict[str, Any] | None:
    done = {ticket["id"] for ticket in tickets if is_done(ticket)}
    candidates = []
    for index, ticket in enumerate(tickets):
        if is_done(ticket) or ticket.get("status") == "blocked":
            continue
        dependencies = ticket.get("depends_on", [])
        if not isinstance(dependencies, list):
            raise RalphError(f"{ticket['id']} depends_on must be an array")
        if all(dependency in done for dependency in dependencies):
            candidates.append((ticket.get("priority", 100), index, ticket))
    return min(candidates, default=(None, None, None), key=lambda item: (item[0], item[1]))[2]


def meaningful_steering(path: Path) -> str:
    if not path.exists():
        return ""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("<!--"):
            lines.append(line)
    return "\n".join(lines).strip()


def build_prompt(project: Path, ticket: dict[str, Any], iteration: int, allow_commit: bool) -> str:
    p = paths(project)
    spec = p["spec"].read_text(encoding="utf-8") if p["spec"].exists() else "(No spec.md found.)"
    steering = meaningful_steering(p["steering"])
    commit_rule = (
        "Commit this verified ticket atomically using the repository's conventions."
        if allow_commit
        else "Do not commit or push."
    )
    return f"""# Ralph iteration {iteration}

Work on exactly one ticket in `{project}` with a fresh context. Read repository
instructions and use the installed `sdlc-orchestrator` skill. Reuse existing
code before creating anything. Do not start another ticket or use parallel
agents to implement other tickets.

## Live steering

{steering or "No live steering instructions."}

If steering contains critical work, resolve only that work, remove the resolved
text from `.sdlc/steering.md`, output `<promise>STEERING:DONE</promise>`, and stop.

## Current ticket

```json
{json.dumps(ticket, indent=2)}
```

## Reviewed specification

{spec}

## Required ticket flow

1. Confirm the ticket's observable outcome and inspect the affected code.
2. Write one failing behavioral test and confirm the expected red state.
3. Implement the smallest vertical slice, reach green, and refactor.
4. Run focused and relevant surrounding tests; use browser/runtime exploration
   and a minimal E2E regression for applicable user-facing behavior.
5. Review the diff and blast radius, then map acceptance criteria to evidence.
6. In `.sdlc/tickets.json`, set only `{ticket['id']}` to `status: "done"` and
   add non-empty `verification_evidence`. {commit_rule}
7. End with exactly `<promise>{ticket['id']}:DONE</promise>` and stop.

If blocked, end with `<promise>BLOCKED:reason</promise>`. If a product or design
choice is required, end with `<promise>DECIDE:question</promise>`. Never weaken
tests or acceptance criteria to produce a completion signal. Never push.
"""


def parse_signal(output: str) -> str | None:
    signals = SIGNAL_RE.findall(output)
    unique = list(dict.fromkeys(signals))
    if len(unique) > 1:
        raise RalphError(f"multiple terminal signals: {', '.join(unique)}")
    return unique[0] if unique else None


def resolve_command(value: Any) -> list[str]:
    if isinstance(value, str):
        command = shlex.split(value)
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        command = list(value)
    else:
        raise RalphError("agent_command must be a string or an array of strings")
    if not command:
        raise RalphError("agent_command is empty; use prompt mode for editor-only agents")
    if not any("{prompt}" in item or "{prompt_file}" in item for item in command):
        raise RalphError("agent_command must contain {prompt} or {prompt_file}")
    if not (Path(command[0]).exists() or shutil.which(command[0])):
        raise RalphError(f"agent command not found: {command[0]}")
    return command


def stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "posix":
        os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()


def run_agent(
    command_template: list[str], prompt: str, prompt_file: Path, project: Path,
    ticket_id: str, iteration: int, timeout: int,
) -> tuple[int, str, bool]:
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(prompt, encoding="utf-8")
    command = [
        item.replace("{prompt_file}", str(prompt_file)).replace("{prompt}", prompt)
        for item in command_template
    ]
    environment = os.environ.copy()
    environment.update(
        RALPH_PROJECT_ROOT=str(project),
        RALPH_TICKET_ID=ticket_id,
        RALPH_ITERATION=str(iteration),
    )
    process = subprocess.Popen(
        command,
        cwd=project,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=os.name == "posix",
    )
    output: list[str] = []

    def collect() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output.append(line)
            print(line, end="", flush=True)

    reader = threading.Thread(target=collect, daemon=True)
    reader.start()
    timed_out = False
    try:
        return_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_process(process)
        return_code = process.returncode if process.returncode is not None else 124
    except KeyboardInterrupt:
        stop_process(process)
        raise
    reader.join(timeout=2)
    return return_code, "".join(output), timed_out


def git_output(project: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=project, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        raise RalphError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def git_head(project: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def preflight(project: Path, require_clean: bool) -> None:
    if not project.is_dir():
        raise RalphError(f"project does not exist: {project}")
    git_output(project, "rev-parse", "--git-dir")
    p = paths(project)
    for key in ("config", "tickets", "state"):
        if not p[key].is_file():
            raise RalphError(f"missing {p[key]}; run init first")
    ticket_list(p["tickets"])
    if require_clean and git_output(project, "status", "--porcelain"):
        raise RalphError("working tree is not clean; commit/stash it or pass --allow-dirty")


def failure_signature(output: str, return_code: int) -> str:
    normalized = re.sub(r"\d+", "<n>", output[-4000:].lower())
    return hashlib.sha256(f"{return_code}:{normalized}".encode()).hexdigest()[:16]


def append_history(project: Path, iteration: int, ticket_id: str, output: str, metadata: dict[str, Any]) -> None:
    p = paths(project)
    p["history"].mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = f"{stamp}-{iteration:03d}-{ticket_id}"
    (p["history"] / f"{stem}.txt").write_text(output, encoding="utf-8")
    write_json(p["history"] / f"{stem}.json", metadata)
    with p["log"].open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n- {metadata['finished_at']} | iteration {iteration} | {ticket_id} | "
            f"{metadata['outcome']} | {metadata['duration_seconds']}s\n"
        )


def save_stop(state_path: Path, state: dict[str, Any], status: str, action: str, blocker: str | None = None) -> None:
    state["status"] = status
    state["next_action"] = action
    if blocker:
        state.setdefault("blockers", []).append(blocker)
    state.setdefault("ralph", {})["updated_at"] = now()
    write_json(state_path, state)


def run_loop(project: Path, args: argparse.Namespace) -> int:
    p = paths(project)
    config = load_json(p["config"])
    require_clean = bool(config.get("require_clean_worktree", True)) and not args.allow_dirty
    preflight(project, require_clean)
    command = resolve_command(args.agent_command or config.get("agent_command"))
    max_iterations = args.max_iterations or int(config.get("max_iterations", 10))
    max_minutes = args.max_minutes or int(config.get("max_minutes", 120))
    timeout = args.iteration_timeout or int(config.get("iteration_timeout_seconds", 1800))
    max_same_failure = args.max_same_failure or int(config.get("max_same_failure", 3))
    allow_commit = bool(args.allow_commit or config.get("allow_commit", False))
    if min(max_iterations, max_minutes, timeout, max_same_failure) < 1:
        raise RalphError("all loop bounds must be positive")

    state = load_json(p["state"])
    ralph = state.setdefault("ralph", {})
    ralph.update(started_at=ralph.get("started_at") or now(), max_iterations=max_iterations, max_minutes=max_minutes)
    state.update(status="active", next_action="Select the next ready ticket.")
    write_json(p["state"], state)
    deadline = time.monotonic() + max_minutes * 60
    previous_signature = ralph.get("failure_signature")
    repeated = int(ralph.get("same_failure_count", 0))

    for _ in range(max_iterations):
        if time.monotonic() >= deadline:
            save_stop(p["state"], state, "paused", "Increase the time budget or resume the loop.")
            return EXIT_BUDGET
        tickets = ticket_list(p["tickets"])
        incomplete = [ticket for ticket in tickets if not (is_done(ticket) and has_evidence(ticket))]
        if not incomplete:
            save_stop(p["state"], state, "complete", "All tickets are verified complete.")
            return EXIT_COMPLETE
        ticket = ready_ticket(tickets)
        if ticket is None:
            reason = "No ticket is ready; inspect blocked, missing, or cyclic dependencies."
            save_stop(p["state"], state, "blocked", reason, reason)
            return EXIT_BLOCKED

        iteration = int(ralph.get("iteration", 0)) + 1
        ralph["iteration"] = iteration
        state.update(current_ticket=ticket["id"], next_action=f"Run {ticket['id']} through the SDLC loop.")
        write_json(p["state"], state)
        prompt = build_prompt(project, ticket, iteration, allow_commit)
        started = time.monotonic()
        code, output, timed_out = run_agent(command, prompt, p["prompt"], project, ticket["id"], iteration, timeout)
        duration = int(time.monotonic() - started)
        try:
            promise = parse_signal(output)
        except RalphError as exc:
            promise = None
            output += f"\nProtocol error: {exc}\n"
        if (timed_out or code != 0) and promise and not (
            promise.startswith("BLOCKED:") or promise.startswith("DECIDE:")
        ):
            output += "\nCompletion signal rejected because the agent process failed.\n"
            promise = None

        outcome = promise or ("TIMEOUT" if timed_out else f"EXIT-{code}")
        append_history(
            project, iteration, ticket["id"], output,
            {"started_at": now(), "finished_at": now(), "duration_seconds": duration,
             "return_code": code, "timed_out": timed_out, "promise": promise, "outcome": outcome},
        )

        if promise and promise.startswith("BLOCKED:"):
            reason = promise.removeprefix("BLOCKED:")
            save_stop(p["state"], state, "blocked", reason, reason)
            return EXIT_BLOCKED
        if promise and promise.startswith("DECIDE:"):
            question = promise.removeprefix("DECIDE:")
            save_stop(p["state"], state, "paused", question)
            return EXIT_DECIDE
        if promise == "STEERING:DONE":
            if meaningful_steering(p["steering"]):
                promise = None
                output += "\nSteering was reported done but the file still contains instructions.\n"
            else:
                repeated = 0
                previous_signature = None
                continue
        if promise == "COMPLETE":
            refreshed = ticket_list(p["tickets"])
            if all(is_done(item) and has_evidence(item) for item in refreshed):
                save_stop(p["state"], state, "complete", "All tickets are verified complete.")
                return EXIT_COMPLETE
            promise = None
            output += "\nCOMPLETE rejected: unfinished or unverified tickets remain.\n"
        expected = f"{ticket['id']}:DONE"
        if promise == expected:
            refreshed = {item["id"]: item for item in ticket_list(p["tickets"])}
            current = refreshed.get(ticket["id"], {})
            if is_done(current) and has_evidence(current):
                completed = state.setdefault("completed_tickets", [])
                if ticket["id"] not in completed:
                    completed.append(ticket["id"])
                state["last_verified_commit"] = git_head(project)
                state["next_action"] = "Select the next ready ticket."
                state["current_ticket"] = None
                repeated = 0
                previous_signature = None
                ralph.update(failure_signature=None, same_failure_count=0, updated_at=now())
                write_json(p["state"], state)
                continue
            promise = None
            output += "\nDONE rejected: ticket status/evidence was not persisted.\n"

        signature = failure_signature(output, code)
        repeated = repeated + 1 if signature == previous_signature else 1
        previous_signature = signature
        ralph.update(failure_signature=signature, same_failure_count=repeated, updated_at=now())
        state.setdefault("failed_attempts", []).append(
            {"iteration": iteration, "ticket": ticket["id"], "signature": signature,
             "return_code": code, "timed_out": timed_out, "at": now()}
        )
        write_json(p["state"], state)
        if repeated >= max_same_failure:
            reason = f"The same failure repeated {repeated} times for {ticket['id']}."
            save_stop(p["state"], state, "blocked", reason, reason)
            return EXIT_BLOCKED

    save_stop(p["state"], state, "paused", "Increase the iteration budget or resume the loop.")
    return EXIT_BUDGET


def show_status(project: Path) -> None:
    p = paths(project)
    state = load_json(p["state"])
    tickets = ticket_list(p["tickets"])
    verified = sum(is_done(ticket) and has_evidence(ticket) for ticket in tickets)
    print(f"Status: {state.get('status', 'unknown')}")
    print(f"Tickets: {verified}/{len(tickets)} verified")
    print(f"Current: {state.get('current_ticket') or '-'}")
    print(f"Next: {state.get('next_action') or '-'}")


def generate_prompt(project: Path, output: Path | None) -> None:
    p = paths(project)
    tickets = ticket_list(p["tickets"])
    ticket = ready_ticket(tickets)
    if ticket is None:
        if all(is_done(item) and has_evidence(item) for item in tickets):
            print("All tickets are verified complete.")
            return
        raise RalphError("no ready ticket; inspect dependencies and blockers")
    state = load_json(p["state"])
    iteration = int(state.setdefault("ralph", {}).get("iteration", 0)) + 1
    prompt = build_prompt(project, ticket, iteration, False)
    target = output or p["prompt"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(prompt, encoding="utf-8")
    print(target)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "prompt", "run"):
        command = sub.add_parser(name)
        command.add_argument("--project", default=".")
        if name == "prompt":
            command.add_argument("--output")
        if name == "run":
            command.add_argument("--agent-command")
            command.add_argument("--max-iterations", type=int)
            command.add_argument("--max-minutes", type=int)
            command.add_argument("--iteration-timeout", type=int)
            command.add_argument("--max-same-failure", type=int)
            command.add_argument("--allow-dirty", action="store_true")
            command.add_argument("--allow-commit", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    project = Path(args.project).expanduser().resolve()
    try:
        if args.command == "init":
            init_project(project)
            return EXIT_COMPLETE
        if args.command == "status":
            show_status(project)
            return EXIT_COMPLETE
        if args.command == "prompt":
            generate_prompt(project, Path(args.output).resolve() if args.output else None)
            return EXIT_COMPLETE
        return run_loop(project, args)
    except RalphError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("Interrupted; state and history were preserved.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
