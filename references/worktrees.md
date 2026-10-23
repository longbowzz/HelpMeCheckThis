# Reviewer worktrees

## Ownership and target

For PR review, the main Agent obtains the required commits and supplies an explicit `head_ref` and `base_ref`. Use `isolation: "git-worktree"` in the confirmed plan. Ref resolution happens once during initialization: every task starts at the same immutable head commit, with the same base and merge-base recorded. Record whether the review compares base..head or merge-base..head; use merge-base..head for the PR-introduced changes when appropriate.

The runner creates one detached Git worktree per task under `RUN_DIR/workspaces/TASK_ID`. This includes native tasks; the main Agent must start those reviewers in the recorded task workspace. CLI cwd and `{workspace}` point to that task's worktree. Evidence and submissions remain under `RUN_DIR/tasks/TASK_ID/`, outside the checkout.

Example plan fields (in addition to stage, domains, tasks, target_digest and confirmation):

```json
{
  "stage": "pr",
  "isolation": "git-worktree",
  "head_ref": "refs/remotes/origin/feature",
  "base_ref": "refs/remotes/origin/main"
}
```

Initialization does not fetch, commit, stash or reset the original checkout. Commit-scoped worktrees exclude staged, unstaged and untracked changes in the source checkout. Explicitly prepare and explain a snapshot strategy when reviewing uncommitted code; never misrepresent a HEAD-only checkout as a working-copy review. The target digest is an independent artifact identifier, not a substitute for resolved Git commit provenance.

## Allowed reviewer operations

Read diffs, show/log commits and inspect the assigned checkout. Checkout existing commits and run agreed tests or experiments in that worktree. Keep worktree-specific changes and test outputs isolated. Record final HEAD, modified/untracked files and experiments; copy evidence to the assigned evidence directory. A fresh worktree does not automatically install ignored dependencies, include local ignored config, initialize every submodule, or isolate external databases, ports and global caches. Report unavailable dependencies and shared external resources.

Worktrees share objects, refs and repository configuration. Reviewers must not fetch, delete/move shared branches, modify repository configuration, run gc/prune, push, or manage worktrees. The main Agent coordinates shared Git operations serially. Do not switch reviewers onto the same named branch; start detached, and preserve any experimental commits before cleanup.

Use a writable permission mode. Codex uses `workspace-write` in its task checkout and a verified `--add-dir` for the separate task artifact directory. Native reviewers receive absolute cwd, context and evidence paths. Worktrees do not enforce access isolation or grant tools permission to write elsewhere.

## Retain, follow up, remove

No worktree is automatically removed on task completion, errors, cancellation, timeout or collection. Partial initialization must preserve any created worktrees and their manifest records.

The main Agent inspects:

```bash
python3 scripts/helpmecheck.py worktrees status RUN_DIR
```

Retain a worktree while clarification, reproduction or follow-up review is likely. Give follow-up reviewers the same path and original commit provenance, note any experiments already performed, and preserve earlier results. Retention alone does not resume a CLI session; use verified host/CLI mechanisms and capture follow-up submissions separately.

When a task is terminal and no follow-up is needed, archive the required evidence and explicitly remove its clean worktree:

```bash
python3 scripts/helpmecheck.py worktrees remove RUN_DIR TASK_ID
```

Removal must validate registration and repository identity, refuse active/pending tasks, and refuse dirty/untracked files or a HEAD different from the pinned target. Do not use force, reset, clean or prune to bypass those checks. Retain blocked worktrees and report their paths until the main Agent deliberately resolves the contents. This command removes only the checkout, not task evidence or run metadata. Main-Agent cleanup decisions remain subject to the host's permission policy.
