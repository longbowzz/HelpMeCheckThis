# Contributing

## Requirements

- Python 3.10 or newer.
- Node.js 20+ for the npm launcher and packaging checks.

No third-party Python packages are required.

## Development checks

Run these from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
python3 scripts/helpmecheck.py --help
node bin/helpmecheck.js --version
npm run check:pack
```

`check:pack` runs `npm pack --dry-run` and fails if required files are missing
or tests, bytecode, local run data, or tarballs would be published.

## Package contents

The npm package is an allowlist defined by `files` in `package.json`. Keep
`SKILL.md`, `references/`, `templates/`, `scripts/`, `bin/`, `LICENSE`, and
`config.example.json` in the package. Do not add tests, local
`.helpmecheckthis/` data, credentials, or generated archives.

## Pull requests

- Keep Skill instructions, reusable templates, and structured field names in
  English.
- Preserve the distinction between reviewer observations and main-Agent
  verification decisions.
- Add or update tests for runner behavior changes.
- Do not commit `.helpmecheckthis/`, `__pycache__/`, or `*.tgz` artifacts.

## Releasing

`0.1.0` was published manually. For subsequent releases:

1. Update `CHANGELOG.md` and bump the version in `package.json` (for example,
   `npm version minor`, which also creates a commit and tag).
2. Run `npm test` and `npm run check:pack`.
3. Push the commit and tag. The release workflow publishes only when that
   version is not already on npm, so re-running a tag is safe.
4. Configure npm Trusted Publishing for `longbowzz/HelpMeCheckThis` and the
   `release.yml` workflow, then remove `registry-url` and `NODE_AUTH_TOKEN`
   from the workflow to publish with OIDC instead of a token.

Do not publish the same version twice; bump it first.

