# Third-party skills and acknowledgements

This project is a curator and installer, not the original author of its
vendored upstream skills. Thank you to the creators and maintainers below.

| Source | What this repository uses | License and pinned source |
|---|---|---|
| [Addy Osmani — agent-skills](https://github.com/addyosmani/agent-skills) | Vendored skill collection; selected skills are in the core profile | MIT; `third_party/LICENSE.addy-osmani`; exact commit in `registry/sources.lock.json` |
| [Cursor pstack](https://github.com/cursor/plugins/tree/main/pstack) | Vendored skill collection; verification and engineering principles in core | MIT; `third_party/LICENSE.pstack`; exact commit in `registry/sources.lock.json` |
| [Matt Pocock — skills](https://github.com/mattpocock/skills) | Vendored skill collection; clarification, specification, tickets, design, and TDD in core | MIT; `third_party/LICENSE.matt-pocock`; exact commit in `registry/sources.lock.json` |
| [Cloudflare — security-audit-skill](https://github.com/cloudflare/security-audit-skill) | Vendored `security-audit` skill and validators; the core security gate | MIT; `third_party/LICENSE.cloudflare-security-audit`; exact commit in `registry/sources.lock.json` |
| [PageAI Pro — ralph-loop](https://github.com/PageAI-Pro/ralph-loop) | Design inspiration for this repository's integrated Ralph runner; its bundled skills are not copied | MIT; `third_party/LICENSE.pageai-ralph-loop`; exact commit in `registry/sources.lock.json` |

The repository's original orchestration and installer code is covered by the
root `LICENSE`. Each upstream retains its own copyright and license notice.
Inclusion does not imply endorsement by the upstream creator.

When refreshing an upstream, preserve its license file, review the diff, and
update the pinned commit. `scripts/sync_upstreams.py` performs the mechanical
copy but deliberately does not commit or publish the result.
