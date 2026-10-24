#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const script = resolve(root, "scripts", "skillctl.py");
const configured = process.env.AGENT_SDLC_PYTHON;
const candidates = configured
  ? [{ command: configured, prefix: [] }]
  : process.platform === "win32"
    ? [{ command: "py", prefix: ["-3"] }, { command: "python", prefix: [] }]
    : [{ command: "python3", prefix: [] }, { command: "python", prefix: [] }];

let selected;
for (const candidate of candidates) {
  const probe = spawnSync(candidate.command, [...candidate.prefix, "--version"], {
    stdio: "ignore",
  });
  if (!probe.error && probe.status === 0) {
    selected = candidate;
    break;
  }
}

if (!selected) {
  console.error(
    "agent-sdlc-skills-manager requires Python 3. Set AGENT_SDLC_PYTHON to its executable if it is not on PATH.",
  );
  process.exit(1);
}

const result = spawnSync(
  selected.command,
  [...selected.prefix, script, ...process.argv.slice(2)],
  { cwd: process.cwd(), stdio: "inherit" },
);
if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
