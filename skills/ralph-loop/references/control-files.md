# Ralph control files

Ralph shares the `.sdlc` workspace with `sdlc-orchestrator`.

| Path | Purpose |
|---|---|
| `.sdlc/spec.md` | Reviewed behavior, constraints, and acceptance criteria |
| `.sdlc/tickets.json` | Ordered task lookup table and per-ticket evidence |
| `.sdlc/run-state.json` | Machine-readable resumable loop state |
| `.sdlc/steering.md` | Live critical instructions checked every iteration |
| `.sdlc/ralph/config.json` | Loop bounds and agent command |
| `.sdlc/ralph/current-prompt.md` | Prompt generated for the next fresh invocation |
| `.sdlc/ralph/log.md` | Compact human-readable progress |
| `.sdlc/ralph/history/` | Raw output and metadata per iteration |

## Ticket shape

```json
{
  "tickets": [
    {
      "id": "TICKET-001",
      "title": "Deliver one observable vertical slice",
      "priority": 10,
      "status": "pending",
      "depends_on": [],
      "acceptance_criteria": ["User-visible behavior is defined"],
      "verification": ["Run the focused test"],
      "verification_evidence": []
    }
  ]
}
```

Statuses are `pending`, `in_progress`, `done`, or `blocked`. A ticket is not
done until `status` is `done` and `verification_evidence` is non-empty.

## Agent command

Use an argument array so the runner executes without a shell. Include exactly
one prompt placeholder:

```json
{
  "agent_command": ["codex", "exec", "{prompt}"],
  "max_iterations": 10,
  "max_minutes": 120,
  "iteration_timeout_seconds": 1800,
  "max_same_failure": 3,
  "allow_commit": false,
  "require_clean_worktree": true
}
```

Use `{prompt_file}` when the CLI accepts a prompt-file path. The runner exports
`RALPH_PROJECT_ROOT`, `RALPH_TICKET_ID`, and `RALPH_ITERATION` for adapters and
test doubles. Keep API keys in the agent's secure environment, never in this
file.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | Every ticket verified complete |
| 1 | Iteration or time budget exhausted |
| 2 | Blocked or repeated failure |
| 3 | Human decision required |
| 4 | Preflight, configuration, or protocol error |
