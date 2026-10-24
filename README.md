# agent-sdlc-skills

A curated, cross-editor software-delivery skill catalog. The repository vendors
121 MIT-licensed upstream skills, but installs only a small default profile into
an editor-visible directory.

## The model

- `catalog/` contains the full upstream catalog and is not an editor discovery path.
- `skills/` contains original orchestration skills maintained in this repository.
- `profiles/core.json` selects 17 upstream skills plus `sdlc-orchestrator` and `ralph-loop`.
- `scripts/skillctl.py` materializes only selected skills into a project.
- `registry/skills.json` is compact routing metadata; agents search it before enabling an optional skill.

Keeping 121 skills in this Git repository does not put all 121 skill bodies into
model context. Only skills copied into the editor's discovery directory are
eligible for discovery, and compatible editors progressively load their bodies.

## Quick start

```bash
git clone https://github.com/shubh0709/agent-sdlc-skills-manager.git
cd agent-sdlc-skills

# Preview the 19-skill core installation
python scripts/skillctl.py apply core --editor agents --project /path/to/project --dry-run

# Install it to /path/to/project/.agents/skills
python scripts/skillctl.py apply core --editor agents --project /path/to/project

# Find optional skills without activating them
python scripts/skillctl.py search security
python scripts/skillctl.py list --stage verify

# Enable one optional skill
python scripts/skillctl.py enable addy-osmani/security-and-hardening --editor agents --project /path/to/project

# Remove that managed skill again
python scripts/skillctl.py disable security-and-hardening --editor agents --project /path/to/project
```

Use `--editor kilo`, `cline`, `cursor`, `claude`, or `codex` for an
editor-specific directory. Prefer `agents` for the portable `.agents/skills`
layout supported by Kilo Code and Codex.

## Default lifecycle

1. Clarify the task by grilling assumptions and modeling the domain.
2. Write the specification and acceptance criteria.
3. Divide the specification into ordered, independently verifiable tickets.
4. Research official sources and design the affected boundaries when needed.
5. Deliver one vertical slice with red-green-refactor TDD.
6. Exercise the real runtime and browser where applicable.
7. Review quality and inspect the blast radius.
8. Verify acceptance criteria with reproducible evidence.
9. Commit an atomic change and continue with the next ticket.

The orchestrator chooses the smallest applicable skill set at each stage. It
does not load every alternative merely because it exists.

## Ralph loop

Ralph is the 19th core skill. Initialize its control files only after a reviewed
specification and ticket set exist:

```bash
python /path/to/project/.agents/skills/ralph-loop/scripts/ralph.py init \
  --project /path/to/project
```

For editors without an agent CLI, generate the next one-ticket prompt and run it
in the editor:

```bash
python /path/to/project/.agents/skills/ralph-loop/scripts/ralph.py prompt \
  --project /path/to/project
```

For CLI-capable agents, configure an argument-vector command in
`.sdlc/ralph/config.json` and run bounded fresh-context iterations. Ralph reuses
the SDLC orchestrator and the existing TDD, review, browser-testing and
verification skills instead of carrying duplicate implementations.

```bash
python /path/to/project/.agents/skills/ralph-loop/scripts/ralph.py run \
  --project /path/to/project \
  --max-iterations 10 \
  --max-minutes 120
```

## Updating the catalog

Each vendored collection retains its original MIT license in `third_party/`.
Pinned source commits live in `registry/sources.lock.json`. After intentionally
updating the vendored content, rebuild routing metadata and run validation:

```bash
python scripts/rebuild_registry.py
python scripts/skillctl.py doctor
python -m unittest discover -s tests -v
```

Do not auto-execute newly imported scripts. Review provenance, license, skill
instructions, and bundled executables before adding a skill to a profile.
