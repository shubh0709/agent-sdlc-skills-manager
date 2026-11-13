

## Shared project work log (required for substantive SDLC work)

Maintain a single project-local `.worklog/` for all skills and subagents, including standalone grilling, requirements, HLD, LLD, design changes, TDD, reviews and verification. Before working, read existing `.worklog/context.md`, `.worklog/questions.md`, `.worklog/hld.md`, `.worklog/lld.md` and `.worklog/decisions.md` if they exist. Never treat an unrecorded assumption as user approval.

Record the original prompt and confirmed understanding under `context`; question/answer/recommendation rounds under `questions`; proposed alternatives and explicitly approved/rejected HLD and LLD under `hld` and `lld`; changed or superseded architectural decisions under `decisions`; milestones, test evidence, handoffs and remaining risks under `progress`. Keep decisions current immediately; summarize routine activity at milestones. Distinguish `proposed`, `discussed`, `approved`, `rejected`, `superseded`, and `observed`; never invent approval. Do not log secrets, credentials, sensitive tool output, or private data without explicit permission.

Use the shared writer rather than directly editing generated summaries (which are projections):

```sh
npx agent-sdlc-skills-manager worklog --project . record --section questions --title "Decision topic" --body-file /path/to/reviewed-note.md --status discussed
npx agent-sdlc-skills-manager worklog --project . render
```

For use from the manager source, run `python3 scripts/worklog.py --project /path/to/project ...`. The writer creates append-only event files, regenerates Markdown summaries and exports an offline `.worklog/index.html` upon `render`. Link design revisions via `--supersedes EVENT_ID`. Verify the generated page locally before handoff; Mermaid fences remain readable as source unless explicitly rendered into supported SVG. Work logs must not replace the HLD -> LLD -> explicit implementation approval gates.
