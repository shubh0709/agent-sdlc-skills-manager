---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
disable-model-invocation: true
---

Call the Skill tool twice, for "grilling" and "domain-modeling".

## Mandatory design discussion before implementation

After clarifying the problem, explicitly ask whether the user wants to discuss HLD. For non-trivial work, strongly recommend it. If accepted, propose at least two viable approaches (or explain why only one is feasible), compare architecture, data/request flows, reliability, scalability, complexity, cost and trade-offs, and have an interactive discussion before recommending a path. Record the selected HLD and obtain explicit approval.

**Only after the HLD discussion is complete**, separately ask whether the user wants to discuss LLD. If accepted, explore APIs, data models, modules, interfaces, error handling, testing and rollout alternatives, then obtain explicit LLD approval.

If either discussion is declined, record that decision without implying design approval. **Never start application code changes or delegate implementation until the user explicitly approves the implementation path after both sequential HLD and LLD checkpoints.** Planning documentation can be written when requested. Keep depth proportionate for trivial tasks.


Read and follow the shared work-log protocol in `skills/sdlc-orchestrator/references/worklog-protocol.md`. All Q&A, HLD, LLD, and subsequent design changes must be recorded before implementation. The installer also adds this protocol to the installed skill copy.
