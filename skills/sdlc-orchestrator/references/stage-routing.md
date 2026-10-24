# Stage routing

| Stage | Default skills | Optional-skill signals | Exit evidence |
|---|---|---|---|
| clarify | grill-with-docs, grilling, domain-modeling | vague idea, adversarial assumptions, unfamiliar domain | agreed problem, constraints, non-goals |
| specify | to-spec | API contract, migration, privacy, accessibility | testable acceptance criteria |
| ticket | to-tickets | parallel work, dependency planning | ordered tickets with proof |
| design | codebase-design, source-driven-development | public interface, data model, framework uncertainty | documented boundary decision |
| implement | incremental-implementation, tdd | language/framework specialty | red-green-refactor evidence |
| test | browser-testing-with-devtools, diagnosing-bugs | performance, accessibility, integration, visual behavior | runtime and regression evidence |
| review | code-review-and-quality, blast-radius | security, migration, performance, API compatibility | findings resolved or dispositioned |
| security | security-audit | explicit full audit, threat-model gap, trust boundary, auth, tenant isolation, secrets, supply chain | findings resolved, accepted, or ticketed with an owner |
| verify | create-verification-skill, principle-prove-it-works | missing project verifier, release proof | every criterion mapped to evidence |
| ship | none by default | deployment, observability, rollout, rollback | launch and rollback readiness |

When alternatives overlap, prefer the already-active core skill. Add an optional
skill only when its description matches a named gap that the default does not
cover.

