# Local Adapter Catalog

The catalog provides disabled-by-default metadata for locally installed command-line agents. Discovery checks executable availability with `shutil.which`; it does not inspect credential files, authenticate, contact a service, or make model calls. Version checks should invoke only each verified `version_args` entry.

| ID | Executable | Supported | Invocation transport | Verified version check |
| --- | --- | --- | --- | --- |
| `claude` | `claude` | Yes | Prompt as final argument; `--print --output-format json` | `claude --version` |
| `codex` | `codex` | Yes | Prompt as final argument to `codex exec --ephemeral --sandbox workspace-write` | `codex --version` |
| `pi` | `pi` | Yes; live review tested | `pi --print --no-session … PROMPT`, using existing model settings | `pi --version` |
| `dsh` | `dsh` | Yes; live review tested with inline evidence fallback | `dsh --profile headless PROMPT` | `dsh --version` |

Supported command options were confirmed from local CLI help. `probe_argv` supplies only the non-interactive invocation shape; probing is an explicit operation and may perform a model call, so discovery must not run it automatically. On 2026-10-23, pi 1.4.0 and official DeepSeek Harness dsh 0.2.1-rc.2 completed real isolated-worktree reviews with DeepSeek Flash; JSON submissions validated. pi wrote external task evidence directly. dsh's workspace-write policy blocked the external evidence directory; it ran local tests and returned inline_evidence successfully. Catalog entries are supported but disabled by default, preserve existing provider/model settings, and still require user-specific capability checks. Pi review defaults suppress extension/MCP/Skill/prompt-template discovery to prevent nested review invocation; core read/write/bash tools remain available. This is not an OS sandbox. dsh starts a new persisted headless session unless an explicit session-id is supplied; headless reads API-key environment/home .env rather than GUI credentials. Its shipped model is deepseek-flash. Inspect its session-log contribution policy before sharing project content; disabling telemetry alone is not equivalent to disabling log contribution.

Each entry has `configured_model: null` and `model_source: "unknown"`. Do not infer runtime model identity from executable names, local configuration, or output text. The catalog does not read credentials or model configuration.

## Permission and invocation checklist

Review tasks require writable evidence and usually temporary test storage. Source preservation is a separate assignment rule. Do not default every reviewer to read-only.

| Reviewer | Normal invocation and permissions | Checks before enabling |
| --- | --- | --- |
| Codex | `codex exec --ephemeral --sandbox workspace-write --add-dir /absolute/task/directory PROMPT`, with the assigned task worktree as cwd | Verify `exec --help`; ensure task evidence and temporary files are writable. For an approved external artifact directory, add `--add-dir /absolute/task/directory` if supported. Workspace-write is not evidence-directory-only isolation. |
| Claude Code | `claude --print --output-format json PROMPT`, using existing configured permissions | Verify `--help`; confirm required read/write/test tools are permitted by the host. Report permission denial; do not add bypass flags. |
| pi / dsh / custom CLI | Explicit argv and prompt transport from that installed CLI's help | Identify the actual command and version; verify non-interactive mode, cwd, write/test permissions, result format and fresh-session behavior. Until verified, keep disabled/discovery-only. |
| Native subagent | Host subagent tool plus absolute assignment/context paths | Explicitly allow review artifact creation and assigned tests within host permissions; do not assume shell CLI flags apply. |

Before the full review, have the reviewer confirm context access, create a small evidence artifact, and check required temporary storage. Keep review artifacts under assigned paths. Record source fingerprints before and after review. Report unexpected source edits without reverting them. A read-only probe that only replies with a token does not establish write/test capability. Probe invocation may differ from the full review; record which capabilities each actually tested.

Existing local configs are not automatically migrated by catalog changes. Replace a previously configured `--sandbox read-only` with `--sandbox workspace-write` for ordinary Codex reviews after selecting the appropriate permissions; retain read-only when explicitly required. Inline text evidence is a fallback for restricted environments.

## Output normalization

`scripts.adapters.catalog.parse_output(adapter, text)` accepts a direct JSON object and returns `{ok, result, error}`. For `claude`, it also unwraps the verified `--output-format json` envelope's string `result` field when that field contains a JSON object. Codex's `--json` output is a stream of event records rather than a documented final-result envelope here, so the helper does not interpret its events; callers must extract and pass a direct result JSON object. Invalid JSON, non-object JSON, and invalid embedded Claude result JSON are reported as errors, never as an empty review result.

The helper preserves result data as supplied and does not synthesize model identity or other provenance.
