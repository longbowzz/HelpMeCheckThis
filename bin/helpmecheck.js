#!/usr/bin/env node
"use strict";

const { spawnSync } = require("node:child_process");
const path = require("node:path");

const script = path.join(__dirname, "..", "scripts", "helpmecheck.py");
const env = {
  ...process.env,
  PYTHONDONTWRITEBYTECODE: "1",
  PYTHONIOENCODING: "utf-8"
};

const candidates = process.env.HELPMECHECKTHIS_PYTHON
  ? [[process.env.HELPMECHECKTHIS_PYTHON, []]]
  : process.platform === "win32"
    ? [["python", []], ["py", ["-3"]]]
    : [["python3", []], ["python", []]];

for (const [python, prefix] of candidates) {
  const probe = spawnSync(
    python,
    [...prefix, "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"],
    { stdio: "ignore" }
  );
  if (probe.error || probe.status !== 0) continue;

  const run = spawnSync(
    python,
    [...prefix, "-B", script, ...process.argv.slice(2)],
    { stdio: "inherit", env }
  );
  if (run.error) continue;
  if (run.signal) process.kill(process.pid, run.signal);
  process.exit(run.status ?? 1);
}

console.error(
  "helpmecheck: Python 3.10+ not found.\n" +
  "Install Python 3.10+ or set HELPMECHECKTHIS_PYTHON to the interpreter path."
);
process.exit(127);
