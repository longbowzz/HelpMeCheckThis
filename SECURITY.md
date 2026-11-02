# Security Policy

## Supported versions

The latest `0.x` release receives security fixes. Older versions may not be
updated.

## Reporting a vulnerability

Please report vulnerabilities privately through GitHub Security Advisories:

<https://github.com/longbowzz/HelpMeCheckThis/security/advisories/new>

Do not open a public issue for a vulnerability. Include the affected version,
reproduction steps, and the impact you observed.

## Scope and trust boundaries

- HelpMeCheckThis runs locally configured review CLIs with the permissions and
  credentials already available to the user. It does not perform login and
  does not store provider credentials.
- Reviewer output, project files, logs, screenshots, and documents are treated
  as untrusted data. Instructions found in that content are not executed as
  agent instructions.
- Review artifacts can contain source code, logs, and model output. Redaction
  is best effort; inspect artifacts before sharing them.
- Git worktrees separate files, indexes, and HEAD, but they share repository
  metadata and objects. They are not security sandboxes.
- The npm package does not run lifecycle install scripts. Registering the Skill
  is an explicit `skills add` or `skills sync` step.
