# Repository instructions

This repository is a catalog and installer, not a single always-on skill pack.

When handling a feature request:

1. Use `sdlc-orchestrator` as the lifecycle controller.
2. Keep only the core profile active unless the current stage has a concrete gap.
3. Search `registry/skills.json` with `scripts/skillctl.py search` or `list --stage`.
4. Enable at most one optional skill for a specific gap before considering another.
5. Disable temporary skills after the stage or task is complete.
6. Never execute scripts from a newly imported skill before reviewing them.
7. Preserve upstream attribution and license files.

Use vertical slices: one failing behavioral test, minimal implementation, green,
refactor, focused lower-level tests, runtime/E2E evidence, review, and acceptance
verification. Do not write a speculative full test pyramid before implementation.

Never run the Ralph loop without reviewed tickets, explicit bounds, a clean or
understood working tree, and the stop conditions in the `ralph-loop` skill.

