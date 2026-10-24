# agent-sdlc-skills

A curated, cross-editor software-delivery skill catalog. The repository vendors
122 MIT-licensed upstream skills, but installs only a small default profile into
an editor-visible directory.

## The model

- `catalog/` contains the full upstream catalog and is not an editor discovery path.
- `skills/` contains original orchestration skills maintained in this repository.
- `profiles/core.json` selects 18 upstream skills plus `sdlc-orchestrator` and `ralph-loop`.
- `scripts/skillctl.py` materializes only selected skills into a project.
- `registry/skills.json` is compact routing metadata; agents search it before enabling an optional skill.

Keeping 122 skills in this Git repository does not put all 122 skill bodies into
model context. Only skills copied into the editor's discovery directory are
eligible for discovery, and compatible editors progressively load their bodies.

## Quick start

Python 3.10+ is required. The shortest installation path is the npm package;
`npx` downloads the catalog temporarily and the CLI copies only the selected
profile into your project:

```bash
# Preview, then install the 20-skill core into the current project
npx agent-sdlc-skills-manager apply core --editor agents --project . --dry-run
npx agent-sdlc-skills-manager apply core --editor agents --project .

# Search and selectively enable one optional skill
npx agent-sdlc-skills-manager search security
npx agent-sdlc-skills-manager enable addy-osmani/security-and-hardening --editor agents --project .
```

To run from source instead:

```bash
git clone https://github.com/shubh0709/agent-sdlc-skills-manager.git
cd agent-sdlc-skills-manager

# Preview the 20-skill core installation
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
8. Run the focused Cloudflare security gate when the change touches a trust boundary.
9. Verify acceptance criteria with reproducible evidence.
10. Commit an atomic change and continue with the next ticket.

The orchestrator chooses the smallest applicable skill set at each stage. It
does not load every alternative merely because it exists.

## Ralph loop

Ralph remains the 19th skill in the original sequence; Cloudflare's security
audit is the 20th core skill. Initialize Ralph's control files only after a reviewed
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

Each upstream URL, branch, layout, license, and pinned commit lives in
`registry/sources.lock.json`. Check for upstream changes without modifying the
working tree:

```bash
python scripts/sync_upstreams.py check
python scripts/sync_upstreams.py check --source cloudflare
```

Refresh one collection at a time. The command clones into a temporary directory,
validates skill frontmatter, replaces only that source's catalog directory,
copies its license, updates the pin, and rebuilds the registry. It never runs
newly imported upstream executables, commits, or publishes:

```bash
python scripts/sync_upstreams.py apply --source cloudflare
git diff --stat
git diff
```

After reviewing an update, run validation:

```bash
python scripts/rebuild_registry.py
python scripts/skillctl.py doctor
python -m unittest discover -s tests -v
```

Do not auto-execute newly imported scripts. Review provenance, license, skill
instructions, and bundled executables before adding a skill to a profile.

## Credits and licensing

This repository is a curated distribution. The original creators are credited
in [THIRD_PARTY.md](THIRD_PARTY.md), every vendored source is pinned, and every
MIT notice is shipped in `third_party/`. The root MIT license applies to this
repository's original installer and orchestration work; upstream copyrights
remain with their authors.

MIT licensing permits redistribution and publication when its copyright and
permission notice are preserved. That is why the npm tarball explicitly includes
`third_party/` and `THIRD_PARTY.md`. This is practical licensing hygiene, not
legal advice; do not import a future source whose license is missing or
incompatible.

Because the catalog includes defensive penetration-testing guidance, the npm
package declares `contentPolicy.class = "dual-use"` and ships the required
`DISCLOSURE` file. The security skill is for authorized, isolated assessment.

## Publishing to npm

The package is configured as the public unscoped package
`agent-sdlc-skills-manager`. Before each release:

```bash
npm test
npm pack --dry-run
npm publish
```

Publishing this dual-use package requires interactive 2FA. Alternatively, use
`npm stage publish` and approve the staged release with 2FA. Do not directly
publish it using a bypass-2FA token or trusted-publishing workflow; npm permits
those methods for dual-use packages only through staged publishing.
