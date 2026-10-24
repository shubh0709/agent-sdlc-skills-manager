---
name: sdlc-orchestrator
description: Orchestrate a complete software-delivery lifecycle from requirements interview through specification, tickets, vertical-slice TDD, implementation, review, runtime testing, and evidence-backed verification. Use for new features, substantial changes, or multi-ticket fixes when the user wants a plan-first workflow, asks to be grilled, requests test-driven development, or wants work shipped through a repeatable SDLC loop. Route to the smallest relevant supporting skill set and discover optional catalog skills only when the core set has a concrete gap.
---

# SDLC Orchestrator

Treat the lifecycle as a state machine with explicit artifacts and exit criteria.
Do not invoke every skill. Select the smallest skill set that closes the current
stage's gap.

## Start the run

1. Inspect repository instructions, status, tests, and relevant code.
2. State the current stage and the artifact needed to exit it.
3. Preserve unrelated working-tree changes.
4. Create `.sdlc/run-state.json` from `references/run-state.schema.json` when the
   work spans multiple tickets or sessions.
5. Read `references/stage-routing.md` for stage-specific defaults and alternatives.

## Run the lifecycle

### 1. Clarify

Use `grill-with-docs` when repository evidence exists; it can combine `grilling`
and `domain-modeling`. Ask one high-leverage question at a time. Surface users,
outcomes, constraints, non-goals, failure modes, and proof. Exit only when the
problem and acceptance boundary are explicit.

### 2. Specify

Use `to-spec`. Convert clarified intent into observable behavior, constraints,
non-goals, failure behavior, and acceptance criteria. Never hide unresolved
product choices inside implementation details.

### 3. Ticket

Use `to-tickets`. Make tickets ordered, independently reviewable, and small
enough for one vertical slice. Record dependencies and a verification command or
observable outcome for every ticket.

### 4. Design and research

Use `codebase-design` only when boundaries or ownership are unclear. Use
`source-driven-development` when framework or library behavior affects the
decision. Record why the chosen design is the smallest coherent change.

### 5. Implement with vertical TDD

Use `incremental-implementation` and `tdd`:

1. Select the highest meaningful, affordable behavior seam.
2. Add one failing behavioral test and prove it fails for the expected reason.
3. Implement the minimum production change that makes it pass.
4. Run the focused test and relevant surrounding suite.
5. Refactor while green.
6. Add lower-level tests for complex logic or boundary cases.
7. Repeat for the next slice.

Do not pre-write an entire speculative unit/integration/E2E pyramid before any
implementation. That tests imagined structure rather than observed behavior.

### 6. Exercise the runtime

Use `browser-testing-with-devtools` for browser behavior. Use
`diagnosing-bugs` when evidence contradicts expectations. Add Playwright or
other E2E coverage for critical paths and reproduced regressions, not every
internal branch.

### 7. Review

Use `code-review-and-quality` and `blast-radius`. Review correctness, security,
maintainability, accessibility, performance, compatibility, tests, and the
actual diff. Resolve material findings or record an explicit disposition.

### 8. Verify

Use `create-verification-skill` when the project lacks a stable verifier. Apply
`principle-prove-it-works`: map each acceptance criterion to reproducible
evidence. Report commands, results, runtime observations, and remaining risks.
Do not equate compilation or a green unit suite with feature completion.

### 9. Close

Update tickets and run state. Commit an atomic coherent change when authorized.
For production release work, search the optional catalog for shipping,
observability, migration, security, or performance skills as required.

## Discover an optional skill

Only search when a concrete capability gap exists. Read
`references/install-context.json` if present, then use its `skillctl` command:

```bash
python <skill-repo>/scripts/skillctl.py search "<gap>"
python <skill-repo>/scripts/skillctl.py list --stage <stage>
```

Explain why the candidate is needed, enable one candidate, and reassess. Disable
temporary skills after the task unless the user promotes them into a profile.

## Pause conditions

Pause and ask for direction when requirements conflict, an action is destructive
or irreversible, credentials or external approval are required, unrelated local
changes block safe work, or the same failure repeats without new evidence.

