import contextlib
import io
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from scripts.helpmecheck import (cancel, collect, create_run, discover, import_result,
                                execute, load_config, main, probe, run_task, validate_plan, validate_result, write_json)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.plan = {"stage": "implementation", "target_digest": "sha256:fixture", "confirmed": True,
                     "domains": ["correctness", "security"], "intensity": "quick",
                     "tasks": [{"task_id": domain, "reviewer_id": "fake", "domain": domain,
                                "language": "English", "methods": ["targeted test"],
                                "assignment": "Check the fixture independently."}
                               for domain in ("correctness", "security")]}
        self.run = create_run(self.root, self.plan, "Fixture context", self.root)

    def result(self, task_id="correctness"):
        return {"schema_version": "1.0", "task_id": task_id, "reviewer_id": "fake", "domain": task_id,
                "target_digest": "sha256:fixture", "review_status": "complete", "scope_checked": ["fixture"],
                "methods_used": ["targeted test"], "checks_performed": ["checked fixture"], "findings": [],
                "assumptions": [], "limitations": [], "evidence": []}

    def config(self, program, **options):
        return {"agents": [{"id": "fake", "enabled": True, "argv": [sys.executable, "-c", program], **options}]}

    def test_multidomain_confirmation_gate(self):
        for key, value in (("confirmed", False), ("domains", ["correctness"])):
            with self.assertRaises(ValueError):
                validate_plan({**self.plan, key: value})

    def test_missing_agent_and_model_unknown(self):
        rows = discover({"agents": [{"id": "missing", "argv": ["not-installed-helpmecheck-123"],
                                      "configured_model": "relay-alias"}]})
        self.assertFalse(rows[0]["present"])
        self.assertIsNone(rows[0]["runtime_model"])
        result = run_task(self.run, {"agents": []}, "correctness")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(collect(self.run)["uncovered_domains"], ["correctness", "security"])

    def test_success_and_coverage(self):
        result = self.result()
        record = run_task(self.run, self.config(f"print({json.dumps(result)!r})"), "correctness")
        self.assertEqual(record["status"], "succeeded")
        self.assertEqual(record["validation_errors"], [])
        self.assertEqual(collect(self.run)["uncovered_domains"], ["security"])
        with self.assertRaises(ValueError):
            run_task(self.run, self.config("print('{}')"), "correctness")

    def test_malformed_success_is_uncovered(self):
        record = run_task(self.run, self.config("print('not json')"), "correctness")
        self.assertEqual(record["status"], "succeeded")
        self.assertTrue(record["validation_errors"])
        self.assertEqual(collect(self.run)["covered_domains"], [])

    def test_failed_process_with_valid_json_is_uncovered(self):
        record = run_task(self.run, self.config(f"print({json.dumps(self.result())!r});raise SystemExit(1)"), "correctness")
        self.assertEqual(record["status"], "failed")
        self.assertEqual(collect(self.run)["covered_domains"], [])

    def test_timeout_preserves_partial_output(self):
        record = run_task(self.run, self.config("import time;print('partial',flush=True);time.sleep(20)",
                                               time_budget_seconds=0.5), "correctness")
        self.assertEqual(record["status"], "timed_out")
        self.assertIn("partial", (self.run / "tasks/correctness/stdout.log").read_text())

    def test_cancellation(self):
        results = []
        worker = threading.Thread(target=lambda: results.append(run_task(
            self.run, self.config("import time;time.sleep(20)"), "correctness")))
        worker.start()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if json.loads((self.run / "tasks/correctness/execution.json").read_text())["status"] == "running":
                break
            time.sleep(0.02)
        cancel(self.run, "correctness")
        worker.join(timeout=4)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results[0]["status"], "cancelled")

    def test_reject_wrong_identity_bad_types_and_path_escape(self):
        folder = self.run / "tasks/correctness"
        result = self.result()
        result.update(target_digest="wrong", checks_performed="not an array", evidence=["../assignment.md"])
        write_json(folder / "result.json", result)
        errors = validate_result(self.run, "correctness")
        self.assertTrue(any("target_digest" in e for e in errors))
        self.assertTrue(any("checks_performed" in e for e in errors))
        self.assertTrue(any("evidence/" in e for e in errors))

    def test_native_import(self):
        manifest = json.loads((self.run / "manifest.json").read_text())
        manifest["tasks"][0]["kind"] = "native_subagent"
        write_json(self.run / "manifest.json", manifest)
        source = self.root / "native.json"
        write_json(source, self.result())
        self.assertEqual(import_result(self.run, "correctness", source), [])
        self.assertEqual(collect(self.run)["covered_domains"], ["correctness"])

    def test_config_validation_and_token_budget(self):
        path = self.root / "config.json"
        for value in (True, -1, 0):
            write_json(path, self.config("pass", token_budget=value))
            with self.assertRaises(ValueError):
                load_config(path)
        record = run_task(self.run, self.config("pass", token_budget=100), "correctness")
        self.assertEqual(record["status"], "blocked")

    def test_parallel_task_failure_does_not_discard_other_results(self):
        from unittest.mock import patch
        path = self.root / "config.json"
        write_json(path, {**self.config("pass"), "max_parallel": 2})
        def fake_run(run, config, task_id):
            if task_id == "correctness":
                raise OSError("fixture execution failure")
            return {"task_id": task_id, "status": "succeeded", "validation_errors": []}
        stream = io.StringIO()
        with patch("scripts.helpmecheck.run_task", side_effect=fake_run), contextlib.redirect_stdout(stream):
            code = main(["run", "all", str(self.run), "--config", str(path)])
        self.assertEqual(code, 1)
        output = json.loads(stream.getvalue())
        self.assertEqual([r["status"] for r in output], ["failed", "succeeded"])

    def test_retained_output_has_shared_limit(self):
        folder = self.run / "tasks/correctness"
        outcome = execute([sys.executable, "-c", "import os;os.write(1,b'a'*2000);os.write(2,b'b'*2000)"],
                          "", self.root, folder, 3, max_output_bytes=1000)
        self.assertEqual(outcome["status"], "failed")
        self.assertLessEqual(sum((folder / name).stat().st_size for name in ("stdout.log", "stderr.log")), 1000)

    def test_probe_argv_and_invalid_utf8_output(self):
        cfg = self.config("pass")
        cfg["agents"][0].update(probe_input_mode="argv", probe_argv=[sys.executable, "-c",
            "import os,sys;assert sys.stdin.read()=='';os.write(1,b'\\xffHELPMECHECKTHIS_PROBE_OK')", "{prompt}"])
        self.assertEqual(probe(cfg, "fake", 3)["probe_status"], "ready")

    def test_completed_task_cannot_be_cancelled(self):
        run_task(self.run, self.config("print('invalid output')"), "correctness")
        result = cancel(self.run, "correctness")
        self.assertFalse(result["cancellation_requested"])
        self.assertEqual(result["status"], "succeeded")

    def test_read_only_inline_evidence_round_trip(self):
        result = self.result()
        result["inline_evidence"] = {"trace.txt": "Source trace with actual observations."}
        result["evidence"] = ["evidence/trace.txt"]
        outcome = run_task(self.run, self.config(f"print({json.dumps(result)!r})"), "correctness")
        self.assertEqual(outcome["validation_errors"], [])
        folder = self.run / "tasks/correctness"
        self.assertEqual((folder / "evidence/trace.txt").read_text().rstrip("\n"), result["inline_evidence"]["trace.txt"])
        self.assertNotIn("inline_evidence", json.loads((folder / "result.json").read_text()))
        self.assertIn("inline_evidence", (folder / "stdout.log").read_text())
        self.assertEqual(collect(self.run)["covered_domains"], ["correctness"])

    def test_inline_evidence_cannot_escape_or_overwrite(self):
        for filename in ("../outside.txt", "/outside.txt", "nested/file.txt", "trace.txt"):
            with self.subTest(filename=filename):
                folder = self.run / "tasks/correctness"
                (folder / "evidence/trace.txt").write_text("original")
                result = self.result()
                result["inline_evidence"] = {filename: "replacement"}
                cfg = self.config(f"print({json.dumps(result)!r})")
                # Separate run per attempt preserves the single-attempt contract.
                attempt = create_run(self.root, self.plan, "context", self.root)
                (attempt / "tasks/correctness/evidence/trace.txt").write_text("original")
                outcome = run_task(attempt, cfg, "correctness")
                self.assertTrue(outcome["validation_errors"])
                self.assertEqual((attempt / "tasks/correctness/evidence/trace.txt").read_text(), "original")

    def test_configured_communication_directory_and_root_override(self):
        config = self.root / "config.json"
        plan = self.root / "plan.json"
        context = self.root / "context.md"
        write_json(config, {"agents": [], "communication_dir": "custom-reviews"})
        write_json(plan, self.plan)
        context.write_text("Review context")
        arguments = ["run", "init", "--config", str(config), "--plan", str(plan),
                     "--context", str(context), "--workspace", str(self.root)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(arguments), 0)
        run = Path(json.loads(output.getvalue())["run_dir"])
        self.assertEqual(run.parent.parent, self.root / "custom-reviews")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(arguments + ["--root", str(self.root / "override")]), 0)
        self.assertEqual(Path(json.loads(output.getvalue())["run_dir"]).parent.parent, self.root / "override")

    def test_duplicate_dispatch_preserves_completed_execution(self):
        run_task(self.run, self.config("print('not json')"), "correctness")
        record_path = self.run / "tasks/correctness/execution.json"
        before = record_path.read_bytes()
        config = self.root / "config.json"
        write_json(config, self.config("print('not json')"))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["run", "all", str(self.run), "--config", str(config)]), 1)
        self.assertEqual(record_path.read_bytes(), before)

    def test_version_check_is_explicit_and_reports_result(self):
        cfg = self.config("pass")
        cfg["agents"][0]["version_args"] = ["-c", "print('fixture-version-1')"]
        self.assertIsNone(discover(cfg)[0]["version"])
        row = discover(cfg, versions=True)[0]
        self.assertEqual(row["version"], "fixture-version-1")
        self.assertEqual(row["version_status"], "succeeded")

    def test_cleanup_permission_error_is_reported(self):
        from unittest.mock import Mock, patch
        from scripts.helpmecheck import stop_group
        proc = Mock(pid=123456)
        proc.poll.return_value = 0
        with patch("scripts.helpmecheck.os.killpg", side_effect=PermissionError("denied")):
            warnings = stop_group(proc)
        self.assertTrue(warnings)

    def test_inline_evidence_rejects_directory_symlink(self):
        folder = self.run / "tasks/correctness"
        (folder / "evidence").rmdir()
        outside = self.root / "outside"
        outside.mkdir()
        (folder / "evidence").symlink_to(outside, target_is_directory=True)
        result = self.result()
        result["inline_evidence"] = {"trace.txt": "text"}
        outcome = run_task(self.run, self.config(f"print({json.dumps(result)!r})"), "correctness")
        self.assertTrue(outcome["validation_errors"])
        self.assertFalse((outside / "trace.txt").exists())

    def test_stage_aliases_require_isolation_and_default_is_persisted(self):
        from scripts.helpmecheck import isolation_mode
        for stage in ("PR", "Pull Request", "pull_request", "pr"):
            with self.subTest(stage=stage):
                plan = {**self.plan, "stage": stage}
                self.assertEqual(isolation_mode(plan), "git-worktree")
                with self.assertRaisesRegex(ValueError, "PR reviews require"):
                    validate_plan({**plan, "isolation": "shared"})
                with self.assertRaisesRegex(ValueError, "explicit head_ref"):
                    validate_plan(plan)
        plan = dict(self.plan)
        plan.pop("intensity")
        run = create_run(self.root, plan, "context", self.root)
        for name in ("plan.json", "manifest.json"):
            self.assertEqual(json.loads((run / name).read_text())["intensity"], "standard")

    def test_precreated_result_never_supplies_coverage(self):
        for stdout in ("not json", "```json\n{}\n```", json.dumps(self.result())):
            with self.subTest(stdout=stdout):
                run = create_run(self.root, self.plan, "context", self.root)
                folder = run / "tasks/correctness"
                write_json(folder / "result.json", self.result())
                old = (folder / "result.json").read_bytes()
                outcome = run_task(run, self.config(f"print({stdout!r})"), "correctness")
                self.assertTrue(outcome["validation_errors"])
                self.assertFalse(outcome["submission_accepted"])
                self.assertEqual((folder / "result.json").read_bytes(), old)
                self.assertEqual(collect(run)["covered_domains"], [])

    def test_accepted_result_digest_detects_later_replacement(self):
        run_task(self.run, self.config(f"print({json.dumps(self.result())!r})"), "correctness")
        result = self.result()
        result["scope_checked"] = ["changed"]
        write_json(self.run / "tasks/correctness/result.json", result)
        self.assertEqual(collect(self.run)["covered_domains"], [])
        self.assertTrue(any("accepted submission" in e for e in validate_result(self.run, "correctness")))

    def test_malformed_paths_and_nonfinite_results_are_per_task_errors(self):
        run_task(self.run, self.config(f"print({json.dumps(self.result('security'))!r})"), "security")
        folder = self.run / "tasks/correctness"
        for path in ("evidence/bad\x00name", "evidence/" + "x" * 1000):
            result = self.result()
            result["evidence"] = [path]
            write_json(folder / "result.json", result)
            summary = collect(self.run)
            self.assertEqual(summary["covered_domains"], ["security"])
            self.assertTrue(summary["tasks"][0]["validation_errors"])
        result["evidence"] = ["evidence/loop"]
        write_json(folder / "result.json", result)
        (folder / "evidence/loop").symlink_to("loop")
        self.assertTrue(collect(self.run)["tasks"][0]["validation_errors"])
        for number in ("NaN", "Infinity", "-Infinity", "1e999"):
            raw = json.dumps(self.result()).replace('"findings": []', '"findings": [], "extra": ' + number)
            (folder / "result.json").write_text(raw)
            self.assertTrue(collect(self.run)["tasks"][0]["validation_errors"])
            run = create_run(self.root, self.plan, "context", self.root)
            outcome = run_task(run, self.config(f"print({raw!r})"), "correctness")
            self.assertTrue(outcome["validation_errors"])
            self.assertEqual(collect(run)["covered_domains"], [])

    def test_materialization_failure_terminalizes_and_preserves_evidence(self):
        folder = self.run / "tasks/correctness"
        provenance = folder / "evidence/inline-evidence-provenance.json"
        provenance.write_text("original")
        result = self.result()
        result["inline_evidence"] = {"trace.txt": "new evidence"}
        outcome = run_task(self.run, self.config(f"print({json.dumps(result)!r})"), "correctness")
        self.assertIn(outcome["status"], {"succeeded", "failed"})
        self.assertTrue(outcome["validation_errors"])
        self.assertEqual(provenance.read_text(), "original")
        self.assertFalse((folder / "evidence/trace.txt").exists())
        self.assertIn("inline_evidence", (folder / "stdout.log").read_text())
        self.assertEqual(collect(self.run)["covered_domains"], [])

    def test_cli_failed_import_can_retry_without_losing_process_outcome(self):
        from unittest.mock import patch
        run_task(self.run, self.config("print('not json')"), "correctness")
        source = self.root / "cli-submission.json"
        source.write_text("invalid json")
        self.assertTrue(import_result(self.run, "correctness", source))
        folder = self.run / "tasks/correctness"
        record = json.loads((folder / "execution.json").read_text())
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["process_status"], "succeeded")
        write_json(source, self.result())
        with patch("scripts.helpmecheck.materialize_inline_evidence", side_effect=OSError("fixture storage failure")):
            self.assertTrue(import_result(self.run, "correctness", source))
        self.assertEqual(import_result(self.run, "correctness", source), [])
        self.assertEqual(collect(self.run)["covered_domains"], ["correctness"])
        self.assertEqual(len(list((folder / "import-attempts").iterdir())), 3)
        with self.assertRaises(ValueError):
            import_result(self.run, "correctness", source)

    def test_native_failed_attempts_preserved_and_corrected_retry_works(self):
        from unittest.mock import patch
        manifest = json.loads((self.run / "manifest.json").read_text())
        manifest["tasks"][0]["kind"] = "native_subagent"
        write_json(self.run / "manifest.json", manifest)
        folder = self.run / "tasks/correctness"
        source = self.root / "native.json"
        (folder / "imported-submission.json").write_text("legacy archive")
        source.write_text("invalid json")
        self.assertTrue(import_result(self.run, "correctness", source))
        write_json(source, self.result())
        with patch("scripts.helpmecheck.materialize_inline_evidence", side_effect=OSError("fixture disk failure")):
            self.assertTrue(import_result(self.run, "correctness", source))
        self.assertEqual(json.loads((folder / "execution.json").read_text())["status"], "failed")
        self.assertEqual(import_result(self.run, "correctness", source), [])
        self.assertEqual(collect(self.run)["covered_domains"], ["correctness"])
        self.assertEqual(len(list((folder / "import-attempts").glob("*/submission.json"))), 3)
        self.assertEqual((folder / "imported-submission.json").read_text(), "legacy archive")

    def test_assignments_and_cli_dispatch_include_budgets_and_locations(self):
        tasks = [{**t, "kind": kind, "time_budget_seconds": 12, "token_budget": 123}
                 for t, kind in zip(self.plan["tasks"], ("native_subagent", "cli"))]
        run = create_run(self.root, {**self.plan, "tasks": tasks}, "context", self.root)
        for task in tasks:
            folder = run / "tasks" / task["task_id"]
            text = (folder / "assignment.md").read_text()
            for expected in ("Time budget seconds: 12", "Token budget: 123", "enforcement:",
                             f"Source workspace: {self.root}", str(folder / "temp")):
                self.assertIn(expected, text)
            self.assertTrue((folder / "temp").is_dir())
        # Null task budgets inherit configured agent defaults in the actual CLI prompt.
        cfg = self.config("import sys;print(sys.stdin.read())", time_budget_seconds=3,
                          token_budget=456, token_budget_enforcement="advisory")
        outcome = run_task(self.run, cfg, "correctness")
        prompt = (self.run / "tasks/correctness/stdout.log").read_text()
        self.assertIn("Time budget seconds: 3 (enforcement: hard", prompt)
        self.assertIn("Token budget: 456 (enforcement: advisory)", prompt)
        self.assertEqual(outcome["time_budget_enforcement"], "hard")


    def test_native_retry_preserves_partial_materialization(self):
        from unittest.mock import patch
        manifest = json.loads((self.run / "manifest.json").read_text())
        manifest["tasks"][0]["kind"] = "native_subagent"
        write_json(self.run / "manifest.json", manifest)
        result = self.result()
        result.update(inline_evidence={"trace.txt": "original trace"}, evidence=["evidence/trace.txt"])
        source = self.root / "native.json"
        write_json(source, result)
        original_open = Path.open
        def fail_provenance(path, *args, **kwargs):
            if path.name == "inline-evidence-provenance.json":
                raise OSError("provenance storage unavailable")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", fail_provenance):
            self.assertTrue(import_result(self.run, "correctness", source))
        trace = self.run / "tasks/correctness/evidence/trace.txt"
        self.assertEqual(trace.read_text().strip(), "original trace")
        result.pop("inline_evidence")
        write_json(source, result)
        self.assertEqual(import_result(self.run, "correctness", source), [])
        self.assertEqual(trace.read_text().strip(), "original trace")
        self.assertEqual(collect(self.run)["covered_domains"], ["correctness"])

    @unittest.skipUnless(sys.platform != "win32", "requires POSIX signals")
    def test_run_all_sigint_cancels_running_and_queued_tasks(self):
        import signal
        import subprocess
        import scripts.helpmecheck as runner
        for parallel in (1, 2):
            with self.subTest(parallel=parallel):
                run = create_run(self.root, self.plan, "context", self.root)
                cfg = self.root / "interrupt-config.json"
                write_json(cfg, {**self.config("import time;time.sleep(30)"), "max_parallel": parallel})
                proc = subprocess.Popen([sys.executable, runner.__file__, "run", "all", str(run),
                                         "--config", str(cfg)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                self.addCleanup(lambda proc=proc: proc.kill() if proc.poll() is None else None)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    states = [json.loads((run / "tasks" / task / "execution.json").read_text())["status"]
                              for task in ("correctness", "security")]
                    if states.count("running") == parallel:
                        break
                    time.sleep(0.02)
                else:
                    self.fail("fixture reviewers never started")
                started = time.monotonic()
                proc.send_signal(signal.SIGINT)
                stdout, stderr = proc.communicate(timeout=7)
                self.assertEqual(proc.returncode, 130, stderr)
                self.assertLess(time.monotonic() - started, 6)
                self.assertEqual([row["status"] for row in json.loads(stdout)], ["cancelled", "cancelled"])
                for task in ("correctness", "security")[:parallel]:
                    record = json.loads((run / "tasks" / task / "execution.json").read_text())
                    self.assertIsNotNone(record["exit_code"])
                if parallel == 1:
                    self.assertFalse((run / "tasks/security/stdout.log").exists())
                self.assertEqual(collect(run)["covered_domains"], [])

    def test_shell_metacharacters_remain_data(self):
        cfg = self.config("import sys;print(sys.argv[1])")
        cfg["agents"][0]["argv"].append("$(touch should-not-exist);literal")
        run_task(self.run, cfg, "correctness")
        self.assertFalse((self.root / "should-not-exist").exists())
        self.assertIn("$(touch", (self.run / "tasks/correctness/stdout.log").read_text())


if __name__ == "__main__":
    unittest.main()
