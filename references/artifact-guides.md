# Artifact-specific review bundles

Use these as starting points, then adjust for risk and context.

## Outcome and action guidance

The archived report supports a decision; the main Agent must also brief the user in the project's working language. Adapt both the verdict and next steps to the reviewed artifact.

| Artifact | Decision to communicate | Actions that follow | Verification / stopping condition |
| --- | --- | --- | --- |
| Plan | Proceed, revise before execution, or validate a critical assumption first | Amend scope/non-goals, resolve alternatives, reorder dependencies, assign a bounded feasibility experiment, clarify positive/negative acceptance criteria | A decision-ready plan with explicit assumptions and measurable criteria; no implementation bug list as a substitute |
| Implementation / pending changes | Ready for integration, fix first, or verification blocked | Prioritize concrete fixes, add regression tests, complete missing requirements; separate optional refactoring | Original failure reproduction fails before the fix and passes after it; relevant existing checks pass |
| PR | Ready for merge consideration, request changes, or insufficient evidence | Identify merge blockers with paths/scenarios, required checks and compatibility/migration work; queue unrelated improvements separately | Blockers addressed and targeted regressions pass against the updated head; recommendation is not authority to merge |
| Documentation | Ready to share, revise, or fact-check first | Correct claims/examples, fill missing reader tasks, align code and terminology, verify cited sources | Intended reader can execute the documented steps; important claims have appropriate sources |
| UI / visual work | Accept for intended flows/viewports, revise, or validate missing states | Specify concrete flow/accessibility/visual changes, states and viewports; prioritize functional blockers over cosmetic preferences | Named interactions and accessibility checks pass; screenshots cover the required states rather than only a happy path |
| Release / operations | Go recommendation, no-go, or conditional readiness | Resolve migration/rollback/monitoring gaps, assign operational owners, rehearse deployment and recovery | Explicit release criteria and rollback evidence; review never performs deployment implicitly |
| Architecture / proposal | Adopt, revise, compare alternatives, or defer | Explain trade-offs, risks, dependency costs and a focused experiment that can change the choice | Decision records assumptions and conditions under which the recommendation should be revisited |

For mixed reviews, explain decisions per stage: e.g. an integration test can pass while the implementation still needs fixes before merging. Avoid generic "review complete" as the outcome.

Each significant action should identify a responsible role (main Agent, implementer, reviewer, maintainer or user), the artifact to produce, and observable completion criteria. Do not invent named owners, estimates or authority. If no actionable defects survive verification, recommend proceeding within the verified scope rather than creating busywork. If evidence is unavailable, name the missing evidence and the smallest useful check; repeating the entire review is not automatically justified.

## Plans

Domains: necessity, requirements, design, completeness, operations, evidence. Methods: adversarial assumptions, alternative comparison, dependency search, failure-mode analysis.

## Implementations

Domains: goal fit, correctness, completeness, security, consistency, maintainability, evidence. Methods: diff/context tracing, repository search, static checks, targeted tests, runtime validation. Add performance or UX where relevant.

## Pull requests

Domains: scope/goal fit, correctness, regression/completeness, security, compatibility, maintainability, verification. Methods: diff review, caller tracing, test execution, adversarial edge cases, independent finding verification.

## Documentation

Domains: goal fit, factual correctness, completeness, consistency, usability, evidence. Methods: implementation cross-check, command execution, link/example validation, adversarial reader review.

## UI and visual deliverables

Domains: goal fit, behavior, accessibility, responsive/visual quality, performance, evidence. Methods: runtime validation, keyboard checks, screenshots at required viewports, state matrix, implementation tracing.

## Release and operations

Domains: correctness, compatibility, security, reliability, performance, operations/rollback, evidence. Methods: migration rehearsal, failure-mode analysis, deployment checks, monitoring/rollback validation, independent verification.
