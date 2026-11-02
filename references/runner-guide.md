# Runner guide

The host Agent normally drives these commands through `SKILL.md`. This guide is for manual setup, debugging and adapter integration. Python 3.10+ is required; there are no third-party dependencies. Resolve the script relative to the installed Skill directory:

- npm install: `<project>/node_modules/help-me-check-this`
- `skills sync`: `.agents/skills/help-me-check-this` (a link to the package)
- manual copy: the directory containing `SKILL.md`

The examples below set `SKILL_DIR` explicitly. After an npm install, `npx helpmecheck …` is equivalent.

## Setup

```bash
SKILL_DIR="$(npm root)/help-me-check-this"   # adjust for skills sync or a manual copy
python3 "$SKILL_DIR/scripts/helpmecheck.py" --version
python3 "$SKILL_DIR/scripts/helpmecheck.py" discover --versions
python3 "$SKILL_DIR/scripts/helpmecheck.py" config --config "$SKILL_DIR/config.example.json" --validate
python3 "$SKILL_DIR/scripts/helpmecheck.py" config --config "$SKILL_DIR/config.example.json" --save .helpmecheckthis/config.json
```

The example enables no reviewers. Edit the saved configuration to enable verified CLI definitions. Existing destination configurations are not overwritten. Discovery makes no model calls; `--versions` runs configured bounded version commands. Model probes are separate explicit operations and may incur charges. Model and relay credentials remain in each CLI's existing configuration.

Time and token budgets default to `null`. POSIX timeouts act on the local process group and do not guarantee cancellation of remote provider work. Generic token budgets are advisory or unsupported; requesting an unsupported token budget blocks dispatch. See [adapters](adapters.md) for invocation and permission requirements and [intensity](intensity.md) for budget semantics.

## Initialize and execute

Prepare a real plan and context using the templates. The example plan has placeholder refs and `confirmed: false`; record actual user confirmation rather than changing the field merely to pass validation.

```bash
python3 "$SKILL_DIR/scripts/helpmecheck.py" run init --config .helpmecheckthis/config.json --plan "$SKILL_DIR/templates/plan.example.json" --context "$SKILL_DIR/templates/context-handoff.md" --workspace /absolute/project
```

Initialization returns `run_dir`. Without `--root`, the configured `communication_dir` is resolved relative to `--workspace`; an explicit `--root` overrides it. Replace `RUN_DIR`, `TASK_ID` and `CONFIG` below with actual values.

```bash
python3 "$SKILL_DIR/scripts/helpmecheck.py" run all RUN_DIR --config CONFIG
python3 "$SKILL_DIR/scripts/helpmecheck.py" run task RUN_DIR TASK_ID --config CONFIG
python3 "$SKILL_DIR/scripts/helpmecheck.py" status RUN_DIR
python3 "$SKILL_DIR/scripts/helpmecheck.py" validate RUN_DIR TASK_ID
python3 "$SKILL_DIR/scripts/helpmecheck.py" collect RUN_DIR
```

Use either `run all` or individual `run task` dispatches. `run all` respects `max_parallel`. CLI tasks are single-attempt; a duplicate dispatch must not overwrite existing execution records. For a CLI rerun, prepare a new run. Failed submission imports can be corrected and imported again; each attempt is retained separately, and an accepted submission cannot be overwritten. CLI imports require a successful original process execution; a failed import does not erase that process outcome or authorize rerunning the CLI. A retained checkout can support host-coordinated follow-up work with separately preserved submissions; retention does not automatically resume a CLI session or permit redispatching a claimed task.

For native subagents, dispatch through host tools using the assignment's absolute context, checkout and evidence paths, then import the submission:

```bash
python3 "$SKILL_DIR/scripts/helpmecheck.py" import-result RUN_DIR TASK_ID --source /absolute/submission.json
```

`collect` validates submissions and reports domain coverage. It does not decide whether findings are true or write a semantic review report. The main Agent verifies, deduplicates and synthesizes results.

## Cancellation and checkout retention

```bash
python3 "$SKILL_DIR/scripts/helpmecheck.py" cancel RUN_DIR TASK_ID
python3 "$SKILL_DIR/scripts/helpmecheck.py" worktrees status RUN_DIR
python3 "$SKILL_DIR/scripts/helpmecheck.py" worktrees remove RUN_DIR TASK_ID
```

Cancellation writes a request for the live runner, avoiding signals to potentially reused PIDs. It cannot stop an abandoned runner or native subagent; cancel native work through host tools. Worktrees are never removed automatically. The main Agent decides retention after reviews and follow-ups; removal refuses active/pending tasks, dirty or untracked contents, changed HEADs and invalid registrations. See [worktree lifecycle](worktrees.md).

## Evidence and troubleshooting

Runs normally live under `.helpmecheckthis/runs/<run-id>/`, ignored by Git. They contain the confirmed plan, context, manifest, assignments, execution records, output, normalized submissions and evidence. Preserve selected reports deliberately; inspect artifacts before sharing because redaction is best effort.

A successful process is not necessarily a valid submission or completed domain review. Inspect `execution.json`, validation errors and coverage separately. A reviewer unable to write files can use the optional `inline_evidence` transport in the [protocol](protocol.md); reviewer-authored text is not independently verified evidence.

Git-isolated runs pin commits, excluding local staged, unstaged and untracked changes. Shared/non-Git runs do not freeze source. The main Agent prepares the correct snapshot and checks provenance before synthesis. Worktrees do not isolate global caches, external services or shared Git configuration.

## Development checks

Run these from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
python3 scripts/helpmecheck.py --help
node bin/helpmecheck.js --version
npm run check:pack
```

Tests use offline fixtures and temporary Git repositories without model calls or login. Live adapter behavior still requires explicit testing with the user's installed CLI and provider configuration.
