"""Offline integration tests using real local Git worktrees."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import helpmecheck as h


class WorktreeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.repo / "source.txt").write_text("base\n")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        (self.repo / "source.txt").write_text("head\n")
        self.git("commit", "-qam", "head")
        self.head = self.git("rev-parse", "HEAD")
        self.git("update-ref", "refs/heads/review-head", self.head)
        self.plan = {"stage": "pr", "target_digest": "fixture", "confirmed": True,
                     "head_ref": "review-head", "base_ref": self.base,
                     "domains": ["correctness", "security"],
                     "tasks": [{"task_id": domain, "reviewer_id": "local", "domain": domain,
                                "language": "English", "assignment": "Review snapshot", "methods": ["inspect"]}
                               for domain in ["correctness", "security"]]}

    def git(self, *args, cwd=None):
        return h.git(cwd or self.repo, *args)

    def create(self):
        self.run = h.create_run(self.root / "runs-root", self.plan, "Review context", self.repo)
        self.manifest = h.read_json(self.run / "manifest.json")
        self.paths = [Path(t["workspace"]) for t in self.manifest["tasks"]]
        return self.run

    def terminal(self, task_id="correctness"):
        h.write_json(h.safe_task_dir(self.run, task_id) / "execution.json", {"status": "succeeded"})

    def test_pr_alias_manifest_records_canonical_stage(self):
        self.plan["stage"] = "Pull Request"
        self.create()
        self.assertEqual(self.manifest["stage"], "pr")
        self.assertEqual(h.read_json(self.run / "plan.json")["stage"], "pr")
        self.assertEqual(self.manifest["intensity"], "standard")
        self.assertEqual(self.manifest["isolation"], "git-worktree")

    def test_pinned_detached_snapshots_independent_files_and_indices(self):
        self.create()
        for task, path in zip(self.manifest["tasks"], self.paths):
            self.assertEqual(task["head"], self.head)
            self.assertEqual(task["base"], self.base)
            self.assertEqual(task["merge_base"], self.base)
            self.assertEqual(self.git("rev-parse", "HEAD", cwd=path), self.head)
            self.assertEqual(self.git("rev-parse", "--abbrev-ref", "HEAD", cwd=path), "HEAD")
            text = (h.safe_task_dir(self.run, task["task_id"]) / "assignment.md").read_text()
            self.assertIn(str(path), text)
            self.assertIn("Do not change shared Git refs", text)
        self.git("update-ref", "refs/heads/review-head", self.base)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.paths[0]), self.head)
        (self.paths[0] / "source.txt").write_text("review edit\n")
        self.git("add", "source.txt", cwd=self.paths[0])
        self.assertEqual((self.paths[1] / "source.txt").read_text(), "head\n")
        self.assertEqual((self.repo / "source.txt").read_text(), "head\n")
        self.assertTrue(self.git("diff", "--cached", cwd=self.paths[0]))
        self.assertEqual(self.git("diff", "--cached", cwd=self.paths[1]), "")
        self.assertEqual(self.git("diff", "--cached"), "")

    def test_cli_cwd_and_workspace_and_evidence_placeholders(self):
        self.create()
        code = ("import pathlib,sys; "
                "pathlib.Path(sys.argv[2], 'evidence', 'cwd.txt').write_text(str(pathlib.Path.cwd())+'\\n'+sys.argv[1]); "
                "print('{}')")
        config = {"agents": [{"id": "local", "enabled": True,
                              "argv": [sys.executable, "-c", code, "{workspace}", "{task_dir}"]}]}
        outcome = h.run_task(self.run, config, "correctness")
        self.assertEqual(outcome["status"], "succeeded")
        evidence = h.safe_task_dir(self.run, "correctness") / "evidence" / "cwd.txt"
        self.assertEqual(evidence.read_text().splitlines(), [str(self.paths[0])] * 2)
        self.assertTrue(self.paths[0].exists())
        self.assertEqual(h.read_json(self.run / "manifest.json")["tasks"][0]["worktree"]["state"], "created")

    def test_cleanup_requires_terminal_and_clean_unchanged_head(self):
        self.create()
        for state in ["pending", "running", "unknown"]:
            h.write_json(h.safe_task_dir(self.run, "correctness") / "execution.json", {"status": state})
            with self.assertRaisesRegex(ValueError, "terminal"):
                h.remove_worktree(self.run, "correctness")
        self.terminal()
        dirty = self.paths[0] / "untracked.txt"
        dirty.write_text("evidence")
        rows = h.worktrees_status(self.run)
        self.assertTrue(rows[0]["dirty"])
        self.assertIn("?? untracked.txt", rows[0]["porcelain"])
        self.assertEqual(rows[0]["activity"], "succeeded")
        with self.assertRaisesRegex(ValueError, "dirty or untracked"):
            h.remove_worktree(self.run, "correctness")
        dirty.unlink()
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--allow-empty", "-qm", "experiment", cwd=self.paths[0])
        self.assertTrue(h.worktrees_status(self.run)[0]["head_changed"])
        with self.assertRaisesRegex(ValueError, "HEAD changed"):
            h.remove_worktree(self.run, "correctness")
        self.assertTrue(self.paths[0].exists())

    def test_successful_cleanup_retains_metadata_and_other_worktrees(self):
        self.create()
        self.terminal()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(h.main(["worktrees", "remove", str(self.run), "correctness"]), 0)
        self.assertEqual(json.loads(output.getvalue())["state"], "removed")
        self.assertFalse(self.paths[0].exists())
        self.assertTrue(self.paths[1].exists())
        rows = h.worktrees_status(self.run)
        self.assertEqual(rows[0]["state"], "removed")
        self.assertIn("removed_at", rows[0])
        self.assertEqual(self.git("rev-parse", "HEAD"), self.head)
        with self.assertRaises(ValueError):
            h.remove_worktree(self.run, "correctness")

    def test_refs_required_and_option_injection_rejected(self):
        for stage in ["pr", "pull_request", "implementation"]:
            for ref in [None, "--help", "-q"]:
                plan = {**self.plan, "stage": stage, "isolation": "git-worktree", "head_ref": ref}
                with self.assertRaises(ValueError):
                    h.create_run(self.root / "invalid", plan, "context", self.repo)
        with self.assertRaises(ValueError):
            h.validate_plan({**self.plan, "isolation": "shared"})
        with self.assertRaises(ValueError):
            h.commit_ref(self.repo, "--help")
        with self.assertRaises(ValueError):
            h.create_run(self.root / "invalid", {**self.plan, "base_ref": "missing"}, "context", self.repo)
        self.assertFalse((self.root / "invalid").exists())

    def test_explicit_refs_allow_dirty_source_and_exclude_local_changes(self):
        (self.repo / "source.txt").write_text("uncommitted\n")
        (self.repo / "local.txt").write_text("untracked\n")
        self.create()
        self.assertEqual((self.paths[0] / "source.txt").read_text(), "head\n")
        self.assertFalse((self.paths[0] / "local.txt").exists())
        self.assertEqual((self.repo / "source.txt").read_text(), "uncommitted\n")

    def test_partial_creation_retained_with_error(self):
        original = h.git
        creations = []

        def fail_second(cwd, *args):
            if args[:2] == ("worktree", "add"):
                creations.append(args)
                if len(creations) == 2:
                    raise ValueError("injected failure")
            return original(cwd, *args)

        with patch.object(h, "git", side_effect=fail_second):
            with self.assertRaisesRegex(ValueError, "recovery manifest"):
                self.create()
        run = next((self.root / "runs-root" / "runs").iterdir())
        manifest = h.read_json(run / "manifest.json")
        self.assertEqual(manifest["tasks"][0]["worktree"]["state"], "created")
        self.assertEqual(manifest["tasks"][1]["worktree"]["state"], "creation_failed")
        self.assertTrue(Path(manifest["tasks"][0]["workspace"]).exists())
        self.assertIn("injected failure", manifest["initialization_error"]["error"])

    def test_reject_wrong_registered_path_and_symlink(self):
        self.create()
        self.terminal()
        task = self.manifest["tasks"][0]
        task["workspace"] = str(self.repo)
        h.write_json(self.run / "manifest.json", self.manifest)
        with self.assertRaisesRegex(ValueError, "path or lifecycle"):
            h.remove_worktree(self.run, "correctness")
        task["workspace"] = str(self.paths[0])
        h.write_json(self.run / "manifest.json", self.manifest)
        moved = self.root / "moved"
        self.paths[0].rename(moved)
        self.paths[0].symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "path or lifecycle"):
            h.remove_worktree(self.run, "correctness")

    def test_status_cli_and_native_assignment_paths(self):
        self.plan["tasks"][0]["kind"] = "native_subagent"
        self.create()
        folder = h.safe_task_dir(self.run, "correctness")
        assignment = (folder / "assignment.md").read_text()
        self.assertIn(str(self.paths[0]), assignment)
        self.assertIn(str(folder / "evidence"), assignment)
        self.assertIn(str(self.run / "context.md"), assignment)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(h.main(["worktrees", "status", str(self.run)]), 0)
        rows = json.loads(output.getvalue())
        self.assertEqual(rows[0]["activity"], "pending")
        self.assertFalse(rows[0]["head_changed"])
        self.assertEqual(rows[0]["porcelain"], "")

    def test_cleanup_rejects_tracked_edits_and_unregistered_directory(self):
        self.create()
        self.terminal()
        (self.paths[0] / "source.txt").write_text("dirty tracked file\n")
        with self.assertRaisesRegex(ValueError, "dirty or untracked"):
            h.remove_worktree(self.run, "correctness")
        # Moving the checkout must not cause cleanup of an unrelated replacement path.
        moved = self.root / "original-checkout"
        self.paths[0].rename(moved)
        self.paths[0].mkdir()
        subprocess.run(["git", "init", "-q", str(self.paths[0])], check=True)
        with self.assertRaisesRegex(ValueError, "different repository"):
            h.remove_worktree(self.run, "correctness")
        self.assertTrue((moved / "source.txt").exists())

    def test_shared_non_git_fixture_backwards_compatible(self):
        plan = {k: v for k, v in self.plan.items() if k not in {"head_ref", "base_ref"}}
        plan["stage"] = "implementation"
        fixture = self.root / "plain"
        fixture.mkdir()
        run = h.create_run(self.root / "shared", plan, "context", fixture)
        manifest = h.read_json(run / "manifest.json")
        self.assertEqual(manifest["isolation"], "shared")
        self.assertEqual(manifest["tasks"][0]["workspace"], str(fixture))
        self.assertEqual(h.worktrees_status(run), [])


if __name__ == "__main__":
    unittest.main()
