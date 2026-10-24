---
name: ralph-loop
description: Run or resume a bounded fresh-context agent loop over an already reviewed specification and ordered ticket set. Use when the user asks for a Ralph loop, autonomous ticket execution, repeated implement-test-review-commit cycles, or a resumable long-running coding workflow. Reuse the SDLC orchestrator for each ticket, enforce one ticket per agent invocation, persist state and evidence, honor live steering, and stop on completion, decisions, blockers, repeated failures, unsafe actions, or exhausted iteration/time budgets.
---

# Ralph Loop

Reuse `sdlc-orchestrator`; do not reproduce its clarification, specification,
TDD, review, browser-testing, or verification instructions. Ralph controls
repetition, isolation, state, and stop conditions.

## Choose the operating mode

- **Editor/manual mode:** Use when Kilo, Cursor, Cline, or another editor has no
  usable agent CLI. Run `scripts/ralph.py prompt --project <repo>`, give the
  generated one-ticket prompt to the editor agent, then repeat after it stops.
- **Automated CLI mode:** Use when an agent CLI can accept a prompt in a new
  process. Configure `agent_command` and run `scripts/ralph.py run`.
- **Sandbox mode:** Put the configured command behind the user's chosen
  container or sandbox. Do not require one sandbox product.

Read `references/control-files.md` before initializing or repairing a run.

## Prepare

1. Finish clarification, specification, and ticket review first.
2. Run `scripts/ralph.py init --project <repo>` once. It never overwrites
   existing control files.
3. Populate `.sdlc/tickets.json` with small, ordered, independently verifiable
   tickets and explicit dependencies.
4. Configure an agent command only for automated mode. Prefer an argument array
   and the `{prompt}` or `{prompt_file}` placeholder; never store credentials.
5. Set explicit iteration and time budgets. Leave `allow_commit` false unless
   the user has authorized per-ticket commits.
6. Start from a clean tree, or explicitly acknowledge existing changes with
   `--allow-dirty`.

## Enforce one-ticket iterations

For each fresh invocation:

1. Read live steering instructions first.
2. Select the highest-priority incomplete ticket whose dependencies are done.
3. Execute that ticket through the SDLC implementation, test, review, and
   verification stages.
4. Require observable verification evidence in the ticket record.
5. Mark exactly that ticket done. Commit atomically only when authorized.
6. Emit exactly one terminal signal and stop:

```text
<promise>TICKET-ID:DONE</promise>
<promise>STEERING:DONE</promise>
<promise>COMPLETE</promise>
<promise>BLOCKED:reason</promise>
<promise>DECIDE:question</promise>
```

Treat a promise as a claim, not proof. The controller must confirm that a
completed ticket is marked done and contains evidence. Accept `COMPLETE` only
when every ticket passes that check.

## Preserve observability

Keep structured truth in `.sdlc/run-state.json` and `.sdlc/tickets.json`. Keep
human-readable summaries in `.sdlc/ralph/log.md` and raw iteration output in
`.sdlc/ralph/history/`. A fresh agent should need the current ticket, relevant
specification, steering, and recent state—not the entire historical transcript.

## Stop instead of thrashing

Stop and preserve `next_action` when:

- the same failure repeats without new evidence;
- the agent returns a blocker or decision signal;
- no ticket is ready because dependencies are blocked or cyclic;
- no trustworthy failing reproduction or verification can be produced;
- requirements conflict or scope must change;
- credentials, external approval, destructive work, or production access are
  required;
- unrelated working-tree changes make the next edit unsafe;
- tests remain flaky;
- the iteration, time, or per-iteration timeout budget is exhausted.

Never weaken tests, quality gates, or acceptance criteria to keep the loop
moving. Never push automatically.

## Clean up

Terminate the current child process on timeout or interruption, retain history,
write the exact stop reason, and leave the repository resumable. Disable Ralph
only if the user deliberately removes it from their core profile.

