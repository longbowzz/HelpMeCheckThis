# Review methods

Assign methods per domain and record what was actually performed.

- **Independent adversarial review**: Try to disprove the intended behavior with counterexamples and misuse. Evidence: concrete scenario and expected/observed result. Limitation: imagination is not reproduction.
- **Independent parallel review**: Give fresh reviewers separate contexts and assignments before sharing findings. Evidence: task manifests and timestamps. Limitation: shared model or source still creates common blind spots.
- **Diff and context tracing**: Inspect the change, then callers, configuration, data flow, and nearby conventions. Evidence: locations and traced paths. Limitation: may miss behavior outside the reachable context.
- **Repository search and reference comparison**: Search usages, analogous implementations, schemas, docs, and dependency constraints. Evidence: queries and matching locations. Limitation: search misses generated or dynamic behavior.
- **Static checks**: Run existing lint, type, schema, dependency, and security checks. Evidence: exact command and output. Limitation: tool coverage and configuration bound the result.
- **Targeted test or minimal reproduction**: Add or run the smallest test that exercises a suspected failure. Evidence: command, fixture, and output. Limitation: a passing case does not prove general correctness.
- **Runtime validation**: Run the application or CLI through key success and failure paths. Evidence: sanitized logs, exit status, and environment assumptions. Limitation: one environment is not all deployments.
- **Screenshot and visual-state check**: Inspect required viewport and states against acceptance criteria or design references. Evidence: screenshot path and viewport. Limitation: screenshots do not prove underlying behavior.
- **Documentation cross-check**: Compare prose and examples with implementation, help output, schemas, and tested commands. Evidence: source locations and command results. Limitation: external facts may require separate confirmation.
- **Threat and abuse analysis**: Identify assets, actors, trust boundaries, misuse paths, and impact. Evidence: threat scenario and control. Limitation: not a penetration test unless explicitly performed.
- **Failure-mode analysis**: Enumerate failure causes, detection, recovery, and residual impact. Evidence: table or reproducible path. Limitation: depends on known operating assumptions.
- **Independent finding verification**: Reproduce or challenge a high-impact finding using a fresh context or different reviewer. Evidence: reproduction result and decision. Limitation: inability to reproduce is not proof of absence.
