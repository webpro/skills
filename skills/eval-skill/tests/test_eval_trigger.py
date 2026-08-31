#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


RUNNER = Path(__file__).resolve().parents[1] / "scripts" / "eval-trigger"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
POSITIVE_QUERY = "Use the example skill for this task."
NEGATIVE_QUERY = "Do the nearby task without this skill."


class EvalTriggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="eval-trigger-test-")
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.bin = self.root / "bin"
        self.skill = self.root / "example-skill"
        self.report = self.root / "report.json"
        self.log = self.root / "argv.jsonl"
        self.config = self.root / "fake-config.json"
        self.bin.mkdir()
        (self.skill / "evals").mkdir(parents=True)
        self.skill_text = textwrap.dedent(
            """\
            ---
            name: example-skill
            description: Example skill for runner tests.
            ---

            # Example
            """
        )
        (self.skill / "SKILL.md").write_text(self.skill_text)
        self.install("claude")
        self.install("codex")
        self.write_cases(
            [
                {"query": POSITIVE_QUERY, "should_trigger": True},
                {"query": NEGATIVE_QUERY, "should_trigger": False},
            ]
        )
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "fire", NEGATIVE_QUERY: "quiet"},
        )
        self.write_fake_agent("claude")
        self.write_fake_agent("codex")
        self.write_fake_security()

    def tearDown(self):
        self.temp.cleanup()

    def install(self, agent, text=None, root=None):
        if root is None:
            config = ".claude" if agent == "claude" else ".codex"
            root = self.home / config / "skills"
        target = root / "example-skill"
        target.mkdir(parents=True, exist_ok=True)
        (target / "SKILL.md").write_text(self.skill_text if text is None else text)
        return target

    def write_cases(self, cases):
        (self.skill / "evals" / "trigger.json").write_text(json.dumps(cases))

    def write_config(self, **values):
        self.config.write_text(json.dumps(values))

    def write_fake_security(self, blob=None):
        """Shadow /usr/bin/security so tests never read the real keychain."""
        fake = self.bin / "security"
        if blob is None:
            fake.write_text("#!/bin/sh\nexit 44\n")
        else:
            payload = self.root / "keychain-blob.json"
            payload.write_text(blob)
            fake.write_text(f"#!/bin/sh\ncat '{payload}'\n")
        fake.chmod(0o755)

    def write_fake_agent(self, name):
        fake = self.bin / name
        fake.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json
                import os
                import sys
                import time
                from pathlib import Path

                name = Path(sys.argv[0]).name
                config = json.loads(Path(os.environ["FAKE_AGENT_CONFIG"]).read_text())
                if name == "claude":
                    profile = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
                    plugin = Path(sys.argv[sys.argv.index("--plugin-dir") + 1]) if "--plugin-dir" in sys.argv else None
                else:
                    profile = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
                    plugin = None
                with Path(os.environ["FAKE_AGENT_LOG"]).open("a") as output:
                    output.write(json.dumps({
                        "agent": name,
                        "argv": sys.argv[1:],
                        "home": os.environ.get("HOME"),
                        "profile": str(profile),
                        "skill_exists": (profile / "skills" / "example-skill" / "SKILL.md").is_file(),
                        "alias_skill_exists": (profile / "skills" / "r0" / "example-skill" / "SKILL.md").is_file(),
                        "auth_exists": (profile / "auth.json").is_file(),
                        "credentials_exists": (profile / ".credentials.json").is_file(),
                        "credentials_is_link": (profile / ".credentials.json").is_symlink(),
                        "credentials_mode": (
                            oct((profile / ".credentials.json").lstat().st_mode & 0o777)
                            if (profile / ".credentials.json").is_file()
                            else None
                        ),
                        "state_exists": (Path(os.environ["HOME"]) / ".claude.json").is_file(),
                        "plugin_skill_exists": bool(plugin and (plugin / "skills" / "example-skill" / "SKILL.md").is_file()),
                        "plugin_manifest_exists": bool(plugin and (plugin / ".claude-plugin" / "plugin.json").is_file()),
                    }) + "\\n")

                if "--version" in sys.argv:
                    print(f"fake-{name} 1.0")
                    raise SystemExit(0)

                if name == "claude":
                    prompt = sys.argv[sys.argv.index("-p") + 1]
                    if "skills available to this session" in prompt:
                        mode = config.get("advertised_mode", "advertised")
                    elif prompt.startswith("Positive control:"):
                        mode = config.get("positive_control", "fire")
                    else:
                        mode = config.get("behaviors", {}).get(prompt, "quiet")
                else:
                    prompt = sys.argv[-1]
                    if prompt.startswith("Positive control:"):
                        mode = config.get("positive_control", "fire")
                    else:
                        mode = config.get("behaviors", {}).get(prompt, "quiet")

                if mode == "nonzero":
                    print("agent failed", file=sys.stderr)
                    raise SystemExit(7)
                if mode == "timeout":
                    time.sleep(1)
                    raise SystemExit(0)
                if mode == "malformed":
                    print("not json")
                    raise SystemExit(0)
                if mode == "terminal_only":
                    terminal = (
                        {"type": "result"}
                        if name == "claude"
                        else {"type": "turn.completed"}
                    )
                    print(json.dumps(terminal))
                    raise SystemExit(0)
                if mode == "output_only":
                    item = {
                        "type": "item.completed",
                        "item": {
                            "type": "command_execution",
                            "command": "printf done",
                            "aggregated_output": os.environ["FAKE_INSTALLED_SKILL"],
                            "exit_code": 0,
                            "status": "completed",
                        },
                    }
                    print(json.dumps(item))
                    print(json.dumps({"type": "turn.completed"}))
                    raise SystemExit(0)
                if mode == "read_only":
                    event = {
                        "type": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "Read",
                                    "input": {"file_path": os.environ["FAKE_INSTALLED_SKILL"]},
                                }
                            ]
                        },
                    }
                    print(json.dumps(event))
                    print(json.dumps({"type": "result"}))
                    raise SystemExit(0)
                if mode == "empty":
                    print(json.dumps({"type": "system", "skills": []}))
                    event = {
                        "type": "assistant",
                        "message": {"content": [{"type": "text", "text": "ok"}]},
                    }
                    print(json.dumps(event))
                    print(json.dumps({"type": "result", "subtype": "success"}))
                    raise SystemExit(0)

                fixtures = Path(os.environ["FAKE_AGENT_FIXTURES"])
                suffix = mode if mode == "advertised" else ("fired" if mode == "fire" else "quiet")
                content = (fixtures / f"{name}-{suffix}.jsonl").read_text()
                content = content.replace("__SKILL_PATH__", os.environ["FAKE_INSTALLED_SKILL"])
                print(content, end="")
                """
            )
        )
        fake.chmod(0o755)

    def run_runner(self, *extra, agent="claude", timeout="2", tmpdir=None):
        config = ".claude" if agent == "claude" else ".codex"
        env = {
            **os.environ,
            **({"TMPDIR": str(tmpdir)} if tmpdir else {}),
            "HOME": str(self.home),
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_AGENT_CONFIG": str(self.config),
            "FAKE_AGENT_FIXTURES": str(FIXTURES),
            "FAKE_AGENT_LOG": str(self.log),
            "FAKE_INSTALLED_SKILL": str(
                self.home / config / "skills" / "example-skill" / "SKILL.md"
            ),
        }
        return subprocess.run(
            [
                str(RUNNER),
                str(self.skill),
                "--agent",
                agent,
                "--runs",
                "1",
                "--workers",
                "1",
                "--model",
                "test-model",
                "--timeout",
                timeout,
                "--json",
                str(self.report),
                *extra,
            ],
            env=env,
            capture_output=True,
            text=True,
        )

    def invocations(self, agent=None):
        entries = [json.loads(line) for line in self.log.read_text().splitlines()]
        return [entry for entry in entries if agent is None or entry["agent"] == agent]

    def read_report(self):
        return json.loads(self.report.read_text())

    def test_valid_corpus_passes_and_preserves_default_claude_adapter(self):
        result = self.run_runner()

        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.read_report()
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"], {"total": 2, "passed": 2, "failed": 0})
        self.assertEqual(report["positive_control"]["status"], "fired")

    def test_nonzero_negative_run_is_infrastructure_error(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "fire", NEGATIVE_QUERY: "nonzero"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("agent exited 7", result.stderr)
        self.assertEqual(self.read_report()["status"], "error")

    def test_timeout_is_infrastructure_error(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "timeout", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner(timeout="0.05")

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("timed out", result.stderr)
        self.assertEqual(self.read_report()["status"], "error")

    def test_empty_advertisement_fails_closed(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="empty",
            behaviors={POSITIVE_QUERY: "fire", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("advertised skill catalog was empty", result.stderr)
        self.assertEqual(self.read_report()["status"], "error")

    def test_positive_control_must_fire_before_cases_run(self):
        self.write_config(
            positive_control="quiet",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "fire", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("positive control did not fire", result.stderr)
        prompts = [entry["argv"] for entry in self.invocations("claude")]
        self.assertFalse(any(POSITIVE_QUERY in argv for argv in prompts))

    def test_valid_routing_failure_exits_one(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "quiet", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.read_report()["status"], "fail")

    def test_claude_uses_selected_model_and_restricts_tools_everywhere(self):
        result = self.run_runner()

        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [
            entry
            for entry in self.invocations("claude")
            if "--version" not in entry["argv"]
        ]
        self.assertEqual(len(calls), 4)
        for call in calls:
            argv = call["argv"]
            self.assertEqual(argv[argv.index("--model") + 1], "test-model")
            self.assertEqual(argv[argv.index("--tools") + 1], "Read,Glob,Grep,Skill")
            self.assertEqual(argv[argv.index("--allowedTools") + 1], "Read,Glob,Grep,Skill")
            self.assertIn("--strict-mcp-config", argv)
            self.assertIn("--restricted", argv)
            self.assertNotIn("--bare", argv)
            self.assertIn("--no-session-persistence", argv)
            self.assertIn("--plugin-dir", argv)
            self.assertNotEqual(call["home"], str(self.home))
            self.assertFalse(call["state_exists"])
            self.assertTrue(call["plugin_skill_exists"])
            self.assertTrue(call["plugin_manifest_exists"])

    def test_matching_source_identity_and_provenance_are_reported(self):
        result = self.run_runner()

        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.read_report()
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["runner"]["path"], str(RUNNER))
        self.assertEqual(len(report["runner"]["sha256"]), 64)
        self.assertEqual(report["agent"]["name"], "claude")
        self.assertEqual(report["agent"]["cli_version"], "fake-claude 1.0")
        self.assertEqual(report["agent"]["requested_model"], "test-model")
        self.assertEqual(report["agent"]["observed_models"], ["claude-test-resolved"])
        self.assertTrue(report["agent"]["tool_policy"]["restricted"])
        self.assertTrue(report["agent"]["tool_policy"]["isolated_home"])
        self.assertTrue(report["agent"]["tool_policy"]["target_plugin_only"])
        self.assertEqual(report["skill"]["source_path"], str(self.skill.resolve() / "SKILL.md"))
        self.assertEqual(len(report["skill"]["source_sha256"]), 64)
        self.assertEqual(report["skill"]["source_sha256"], report["skill"]["installed_sha256"])
        self.assertEqual(len(report["eval"]["corpus_sha256"]), 64)
        self.assertEqual(
            report["eval"]["policy_context"],
            {"user_instructions": "isolated", "project_instructions": "fixture_only"},
        )
        self.assertIn("started_at", report)
        self.assertIn("duration_seconds", report)
        trace = report["preflight"]["trace"]
        self.assertTrue(trace["stdout_path"].endswith("preflight.stdout.jsonl"))
        self.assertTrue(Path(trace["stdout_path"]).exists())
        self.assertTrue(Path(trace["stderr_path"]).exists())
        case_trace = report["results"][0]["outcomes"][0]["trace"]
        self.assertTrue(Path(case_trace["stdout_path"]).exists())
        self.assertTrue(Path(case_trace["stderr_path"]).exists())

    def test_stale_same_name_install_fails(self):
        installed = self.home / ".claude" / "skills" / "example-skill" / "SKILL.md"
        installed.write_text(self.skill_text.replace("runner tests", "stale copy"))

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("does not match source", result.stderr)
        self.assertEqual(self.read_report()["status"], "error")

    def test_ambiguous_same_name_installs_fail(self):
        self.install(
            "claude",
            text=self.skill_text.replace("runner tests", "other copy"),
            root=self.home / ".agents" / "skills",
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("conflicting installed copies", result.stderr)

    def test_symlinked_installs_are_deduplicated_by_canonical_path(self):
        agents_root = self.home / ".agents" / "skills"
        agents_root.mkdir(parents=True)
        source = self.home / ".claude" / "skills" / "example-skill"
        (agents_root / "example-skill").symlink_to(source, target_is_directory=True)

        result = self.run_runner()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.read_report()["skill"]["installed_paths"]), 1)

    def test_explicit_installed_skill_handles_nonstandard_root(self):
        standard = self.home / ".claude" / "skills" / "example-skill" / "SKILL.md"
        standard.unlink()
        custom = self.install("claude", root=self.root / "custom")

        result = self.run_runner("--installed-skill", str(custom))

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_installed_skill_does_not_hide_stale_standard_copy(self):
        standard = self.home / ".claude" / "skills" / "example-skill" / "SKILL.md"
        standard.write_text(self.skill_text.replace("runner tests", "stale copy"))
        custom = self.install("claude", root=self.root / "custom")

        result = self.run_runner("--installed-skill", str(custom))

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("conflicting installed copies", result.stderr)

    def test_setup_requires_opt_in_and_then_runs_hermetically(self):
        marker = self.root / "setup-ran"
        os.environ["EVAL_TRIGGER_TEST_MARKER"] = str(marker)
        self.addCleanup(os.environ.pop, "EVAL_TRIGGER_TEST_MARKER", None)
        setup = (
            'test "$GIT_CONFIG_GLOBAL" = /dev/null && '
            'test "$GIT_CONFIG_SYSTEM" = /dev/null && '
            'test ! -t 0 && printf ran >"$EVAL_TRIGGER_TEST_MARKER"'
        )
        self.write_cases(
            [{"query": NEGATIVE_QUERY, "should_trigger": False, "setup": setup}]
        )

        refused = self.run_runner()

        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertIn("--allow-setup", refused.stderr)
        self.assertFalse(marker.exists())

        allowed = self.run_runner("--allow-setup")

        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertEqual(marker.read_text(), "ran")

    def test_setup_failure_is_infrastructure_error(self):
        self.write_cases(
            [{"query": NEGATIVE_QUERY, "should_trigger": False, "setup": "exit 9"}]
        )

        result = self.run_runner("--allow-setup")

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("fixture setup exited 9", result.stderr)
        self.assertEqual(self.read_report()["status"], "error")

    def test_fixture_file_cannot_escape_workspace(self):
        escaped = self.skill / "escaped.txt"
        self.write_cases(
            [
                {
                    "query": NEGATIVE_QUERY,
                    "should_trigger": False,
                    "files": {"../escaped.txt": "bad"},
                }
            ]
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("escapes the fixture workspace", result.stderr)
        self.assertFalse(escaped.exists())

    def test_malformed_event_stream_is_infrastructure_error(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "malformed", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("invalid JSONL", result.stderr)

    def test_terminal_only_stream_is_infrastructure_error(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "terminal_only", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("no response activity", result.stderr)

    def test_codex_adapter_uses_read_only_ephemeral_command(self):
        auth = self.home / ".codex" / "auth.json"
        auth.write_text("{}")
        result = self.run_runner(agent="codex")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = self.read_report()
        self.assertEqual(report["agent"]["name"], "codex")
        self.assertEqual(report["agent"]["observed_models"], [])
        calls = [
            entry
            for entry in self.invocations("codex")
            if "--version" not in entry["argv"]
        ]
        self.assertEqual(len(calls), 3)
        for call in calls:
            argv = call["argv"]
            self.assertIn("--ephemeral", argv)
            self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
            self.assertEqual(argv[argv.index("--model") + 1], "test-model")
            self.assertIn("--skip-git-repo-check", argv)
            self.assertIn("--ignore-user-config", argv)
            self.assertIn("--ignore-rules", argv)
            self.assertNotEqual(call["home"], str(self.home))
            self.assertNotEqual(call["profile"], str(self.home / ".codex"))
            self.assertTrue(call["skill_exists"])
            self.assertTrue(call["auth_exists"])
            self.assertTrue(call["alias_skill_exists"])

    def test_claude_requires_the_authoritative_skill_event(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "read_only", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner()

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.read_report()["results"][0]["trigger_rate"], 0.0)

    def test_codex_does_not_treat_command_output_as_a_skill_read(self):
        self.write_config(
            positive_control="fire",
            advertised_mode="advertised",
            behaviors={POSITIVE_QUERY: "output_only", NEGATIVE_QUERY: "quiet"},
        )

        result = self.run_runner(agent="codex")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.read_report()["results"][0]["trigger_rate"], 0.0)

    def test_claude_auth_passthrough_is_opt_in(self):
        result = self.run_runner()

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = self.invocations("claude")
        self.assertTrue(invocations)
        for entry in invocations:
            self.assertFalse(entry["credentials_exists"])
        self.assertEqual(
            self.read_report()["agent"]["auth"],
            {"passthrough_requested": False, "mechanism": None},
        )

    def test_claude_auth_passthrough_links_a_stored_credentials_file(self):
        stored = self.home / ".claude" / ".credentials.json"
        stored.parent.mkdir(parents=True, exist_ok=True)
        stored.write_text('{"claudeAiOauth": {"accessToken": "stored"}}')

        result = self.run_runner("--auth-passthrough")

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = self.invocations("claude")
        self.assertTrue(invocations)
        for entry in invocations:
            self.assertTrue(entry["credentials_exists"])
            self.assertTrue(entry["credentials_is_link"])
        self.assertEqual(
            self.read_report()["agent"]["auth"],
            {"passthrough_requested": True, "mechanism": "credentials_file"},
        )

    @unittest.skipUnless(sys.platform == "darwin", "keychain path is macOS only")
    def test_claude_auth_passthrough_materializes_the_keychain_blob_privately(self):
        self.write_fake_security('{"claudeAiOauth": {"accessToken": "keychain"}}')

        result = self.run_runner("--auth-passthrough")

        self.assertEqual(result.returncode, 0, result.stderr)
        invocations = self.invocations("claude")
        self.assertTrue(invocations)
        for entry in invocations:
            self.assertTrue(entry["credentials_exists"])
            self.assertFalse(entry["credentials_is_link"])
            self.assertEqual(entry["credentials_mode"], "0o600")
        self.assertEqual(
            self.read_report()["agent"]["auth"],
            {"passthrough_requested": True, "mechanism": "macos_keychain"},
        )

    def test_claude_auth_passthrough_without_credentials_fails_closed(self):
        result = self.run_runner("--auth-passthrough")

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("found no Claude credentials", result.stderr)

    @unittest.skipUnless(sys.platform == "darwin", "keychain path is macOS only")
    def test_claude_auth_passthrough_removes_the_materialized_blob(self):
        self.write_fake_security('{"claudeAiOauth": {"accessToken": "keychain"}}')
        scratch = self.root / "scratch"
        scratch.mkdir()

        result = self.run_runner("--auth-passthrough", tmpdir=scratch)

        # The blob has to have existed during the run for its absence to mean
        # anything, and the search stays inside this test's own temp root so a
        # concurrent eval cannot answer for it.
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            all(entry["credentials_exists"] for entry in self.invocations("claude"))
        )
        self.assertEqual(list(scratch.rglob(".credentials.json")), [])


if __name__ == "__main__":
    unittest.main()
