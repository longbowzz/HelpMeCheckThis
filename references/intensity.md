# Review intensity

Intensity changes depth and evidence requirements. Every level still covers multiple applicable domains.

## Levels

- **quick**: Use for low-risk or time-sensitive changes. Select several high-value domains, inspect the target and immediate context, and run cheap existing checks. Report limited coverage explicitly; do not promise completeness.
- **standard**: Default for ordinary work. Use multiple independent domain tasks, inspect relevant surrounding code or references, run available tests/checks, and require evidence for material findings.
- **deep**: Use for high-impact, complex, security-sensitive, or difficult-to-reverse work. Trace dependencies and failure paths, run targeted validation, preserve artifacts, and independently verify important findings.
- **meticulous**: Use when explicitly requested or when the delivery bar is unusually high. Explore boundary cases, wording, compatibility, UX states, operations, and negative evidence; separate substantive defects from preferences and document residual uncertainty.

## Budgets and status

Default `time_budget_seconds` and `token_budget` are `null`, meaning no user-configured limit. Enforcement labels are `hard`, `advisory` or `unsupported`. CLI time enforcement is `hard` for the local process deadline only, with best-effort process-group cleanup and reported warnings; remote provider work and spend are not guaranteed to stop. Native-host time and token budgets are advisory unless that host independently enforces them. Generic CLI token enforcement is advisory or unsupported; requesting an unsupported token cap blocks dispatch. `null` means no limit is configured, not that an actual cap was enforced.

A local wall-clock timeout should preserve partial output and mark the task `timed_out`. Token usage must never be inferred from character count and must never be claimed when the CLI does not expose it. Intensity is not permission to bypass host approvals, sandbox rules, or user confirmation.
