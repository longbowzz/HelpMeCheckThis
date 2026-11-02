#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const packed = spawnSync(npm, ["pack", "--dry-run", "--json"], {
  cwd: root,
  encoding: "utf8"
});

if (packed.status !== 0) {
  process.stderr.write(packed.stderr || packed.stdout || "npm pack failed\n");
  process.exit(packed.status ?? 1);
}

let parsed;
try {
  parsed = JSON.parse(packed.stdout);
} catch {
  process.stderr.write(`could not parse npm pack output:\n${packed.stdout}\n`);
  process.exit(1);
}

// npm <= 11 returns an array; npm 12 returns an object keyed by package name.
const reports = Array.isArray(parsed) ? parsed : Object.values(parsed);
const report = reports.find((entry) => Array.isArray(entry && entry.files));
if (!report) {
  process.stderr.write(`npm pack output did not contain a file list:\n${packed.stdout}\n`);
  process.exit(1);
}

const files = report.files.map((entry) => entry.path).sort();
const required = [
  "SKILL.md",
  "README.md",
  "README.zh-CN.md",
  "LICENSE",
  "config.example.json",
  "bin/helpmecheck.js",
  "scripts/helpmecheck.py",
  "scripts/adapters/catalog.py",
  "references/protocol.md",
  "templates/final-report.md"
];
const forbiddenSegments = new Set([
  "__pycache__",
  ".helpmecheckthis",
  "node_modules",
  "tests"
]);

const missing = required.filter((requiredPath) => !files.includes(requiredPath));
const forbidden = files.filter((file) => {
  if (file.endsWith(".pyc") || file.endsWith(".tgz")) return true;
  return file.split("/").some((segment) => forbiddenSegments.has(segment));
});

if (missing.length > 0 || forbidden.length > 0) {
  if (missing.length > 0) {
    console.error(`missing required files:\n  ${missing.join("\n  ")}`);
  }
  if (forbidden.length > 0) {
    console.error(`forbidden files in package:\n  ${forbidden.join("\n  ")}`);
  }
  process.exit(1);
}

const sizeKb = (report.size / 1024).toFixed(1);
console.log(`pack check ok: ${files.length} files, ${sizeKb} kB packed`);
