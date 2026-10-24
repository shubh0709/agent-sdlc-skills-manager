---
name: ralph-loop
description: Run a bounded autonomous implementation loop over an already reviewed specification and ordered ticket set. Use only when the user explicitly asks for a Ralph loop, autonomous ticket execution, or repeated implement-test-review-commit cycles. Require explicit iteration or time bounds, persist structured run state, use the SDLC orchestrator inside each ticket, and stop at ambiguity, safety, approval, or repeated-failure gates.
---

# Ralph Loop

Do not start from a vague feature request. Require a reviewed specification,
acceptance criteria, ordered tickets, an understood working tree, verification
commands, and an explicit iteration or time budget.

## Initialize

1. Read the `sdlc-orchestrator` skill.
2. Create or resume `.sdlc/run-state.json`.
3. Confirm the next ticket is unblocked and fits one reviewable vertical slice.
4. Record the loop budget and current commit.

## Iterate

For one ticket at a time:

1. Restate its observable outcome and proof.
2. Add one failing behavioral test; confirm the expected red state.
3. Implement the minimum change; reach green.
4. Refactor and run the relevant surrounding tests.
5. Exercise the runtime or browser when applicable.
6. Review the diff and blast radius.
7. Verify acceptance evidence.
8. Update run state and commit atomically when authorized.
9. Select the next unblocked ticket only if budget remains.

Never bypass a failing test, weaken a quality gate, delete coverage merely to
reach green, or silently broaden scope.

## Stop immediately

Stop and report the exact state when any condition holds:

- the same failure occurs three times without new evidence;
- no trustworthy failing reproduction can be produced;
- requirements or acceptance criteria conflict;
- an action is destructive, irreversible, or production-affecting;
- credentials, external approval, or a product decision are required;
- unrelated working-tree changes make the next edit unsafe;
- a test is persistently flaky;
- the next ticket is blocked;
- the iteration or time budget is exhausted.

On stop, preserve evidence and write `next_action`; do not claim completion.

