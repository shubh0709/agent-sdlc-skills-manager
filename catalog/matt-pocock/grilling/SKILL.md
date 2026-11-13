---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes" accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

## Mandatory design discussion before implementation

After clarifying the problem, explicitly ask whether the user wants to discuss HLD. For non-trivial work, strongly recommend it. If accepted, propose at least two viable approaches (or explain why only one is feasible), compare architecture, data/request flows, reliability, scalability, complexity, cost and trade-offs, and have an interactive discussion before recommending a path. Record the selected HLD and obtain explicit approval.

**Only after the HLD discussion is complete**, separately ask whether the user wants to discuss LLD. If accepted, explore APIs, data models, modules, interfaces, error handling, testing and rollout alternatives, then obtain explicit LLD approval.

If either discussion is declined, record that decision without implying design approval. **Never start application code changes or delegate implementation until the user explicitly approves the implementation path after both sequential HLD and LLD checkpoints.** Planning documentation can be written when requested. Keep depth proportionate for trivial tasks.


Read and follow the shared work-log protocol in `skills/sdlc-orchestrator/references/worklog-protocol.md`. All Q&A, HLD, LLD, and subsequent design changes must be recorded before implementation. The installer also adds this protocol to the installed skill copy.
