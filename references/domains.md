# Review domains

Select several domains that fit the artifact. Do not use the list as a mechanical checklist.

## Core domains

- **Necessity and goal fit**: Is the work needed, and does it solve the stated problem without speculative scope?
- **Requirements and scope**: Are explicit, implicit, and non-functional requirements represented? Are exclusions and acceptance criteria clear?
- **Design reasonableness**: Are assumptions, trade-offs, dependencies, and complexity proportionate? Is there a simpler safe option?
- **Correctness**: Do logic, claims, calculations, interfaces, commands, and behavior produce the intended result?
- **Completeness and edge cases**: Are normal, boundary, empty, malformed, concurrent, and failure paths covered?
- **Consistency and compatibility**: Do code, plan, APIs, configuration, documentation, conventions, and versions agree?
- **Security and privacy**: Check trust boundaries, authorization, injection, secrets, data exposure, unsafe operations, dependencies, and abuse cases.
- **Reliability and recovery**: Check retries, idempotency, cancellation, partial failure, rollback, persistence, and observability.
- **Performance and scalability**: Check algorithmic cost, I/O, concurrency, resource limits, latency, and growth assumptions.
- **Maintainability and readability**: Check structure, reuse, naming, coupling, testability, and future change cost.
- **Usability, accessibility, and visual quality**: Check user flow, error messages, keyboard/screen-reader concerns, responsive behavior, and visual states.
- **Operations and release**: Check deployment, migrations, monitoring, compatibility, rollout, rollback, and ownership.
- **Documentation and communication**: Check accuracy, runnable examples, terminology, audience fit, and unsupported promises.
- **Evidence and verifiability**: Check whether important claims have reproducible tests, logs, screenshots, citations, or clear limits.

## Selection guidance

- Plans: necessity, requirements, design, completeness, risk, operability, evidence.
- Implementations: correctness, completeness, security, consistency, maintainability, tests; add performance or UX when relevant.
- PRs: scope/goal fit, diff correctness, regression/completeness, security, compatibility, maintainability, verification.
- Documents: goal fit, factual correctness, completeness, consistency, audience/usability, examples, evidence.
- UI/visual work: goal fit, behavior/correctness, accessibility, responsive/visual states, performance, evidence.
- Releases: correctness, compatibility, security, reliability, operations/rollback, evidence.
