#!/usr/bin/env python3
"""Behavioral tests for scripts/reviewers against disposable Git fixtures and a fake gh."""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reviewers"
NOW = time.time()

FAKE_GH = r'''#!/usr/bin/env python3
import json, os, re, sys
data = json.load(open(os.environ["FAKE_GH_DATA"]))
args = sys.argv[1:]
with open(os.environ["FAKE_GH_LOG"], "a") as log:
    log.write(" ".join(args[:2]) + "\n")
if data.get("fail"):
    print("gh: simulated failure", file=sys.stderr)
    sys.exit(1)
if args[:2] == ["pr", "view"]:
    if data.get("pr_view") is None:
        print("no pull requests found", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(data["pr_view"]))
    sys.exit(0)
if args[:2] == ["api", "graphql"]:
    query = next(a for a in args if a.startswith("query="))
    with open(os.environ["FAKE_GH_QUERIES"], "a") as sink:
        sink.write(query + "\n")
    if "search(" in query:
        print(json.dumps({"data": {"search": {"nodes": data.get("search", [])}}}))
        sys.exit(0)
    repository = {}
    for alias, number in re.findall(r'(p\d+): pullRequest\(number: (\d+)\)', query):
        repository[alias] = data.get("pulls", {}).get(number)
    for alias, oid in re.findall(r'(c\d+): object\(oid: "([0-9a-f]+)"\)', query):
        info = data["commits"].get(oid)
        if info is None:
            repository[alias] = None
            continue
        repository[alias] = {
            "oid": oid,
            "author": {"user": {"login": info["login"]} if info.get("login") else None},
            "associatedPullRequests": {"nodes": [info["pr"]] if info.get("pr") else []},
        }
    print(json.dumps({"data": {"repository": repository}}))
    sys.exit(0)
print("unexpected gh invocation: " + " ".join(args), file=sys.stderr)
sys.exit(2)
'''


def user(login):
    return {"login": login, "__typename": "User"}


def bot(login):
    return {"login": login, "__typename": "Bot"}


def pull(number, author, *reviews):
    return {"number": number, "author": author,
            "reviews": {"nodes": [{"author": who, "state": state} for who, state in reviews]}}


class Fixture:
    def __init__(self, root):
        self.root = Path(root)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        (self.root / "gitconfig").write_text("")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        gh = self.bin / "gh"
        gh.write_text(FAKE_GH)
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.data = self.root / "gh.json"
        self.log = self.root / "gh.log"
        self.queries = self.root / "gh.queries"
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "FAKE_GH_DATA": str(self.data),
            "FAKE_GH_LOG": str(self.log),
            "FAKE_GH_QUERIES": str(self.queries),
        }
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "Tester")
        self.git("config", "user.email", "tester@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.git("remote", "add", "origin", "git@github.com:acme/widgets.git")

    def git(self, *args, env=None):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True,
                              text=True, env=env or self.env).stdout

    def commit(self, name, email, days_ago, message, files=None, merge=None):
        date = datetime.fromtimestamp(NOW - days_ago * 86400, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        env = {**self.env, "GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_AUTHOR_DATE": date,
               "GIT_COMMITTER_NAME": name, "GIT_COMMITTER_EMAIL": email, "GIT_COMMITTER_DATE": date}
        if merge:
            self.git("merge", "-q", "--no-ff", "-m", message, merge, env=env)
        else:
            for path, content in (files or {}).items():
                target = self.repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                self.git("add", path)
            self.git("commit", "-q", "-m", message, env=env)
        return self.git("rev-parse", "HEAD").strip()

    def run(self, *args, github=None, cwd=None):
        env = dict(self.env)
        self.log.write_text("")
        self.queries.write_text("")
        if github is not None:
            self.data.write_text(json.dumps(github))
            env["PATH"] = f"{self.bin}{os.pathsep}{env['PATH']}"
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or self.repo,
                              capture_output=True, text=True, env=env)


def rows(output):
    """Reviewer rows as dicts, in display order."""
    lines = output.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Reviewer"))
    parsed = []
    for line in lines[start + 2:]:
        if not line.strip():
            break
        cells = [c.strip() for c in line.split("|")]
        parsed.append({"who": cells[0], "score": cells[1], "reviewed": int(cells[2]),
                       "authored": int(cells[3]), "last": cells[4], "match": cells[5]})
    return parsed


class ReviewersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="reviewers-test.")
        f = cls.fx = Fixture(cls.tmp.name)
        cls.c1 = f.commit("Alice", "alice@example.com", 200, "add a (#1)",
                          {"src/a.txt": "a\n", "src/util.txt": "u\n"})
        cls.c2 = f.commit("Bob", "bob@example.com", 20, "tweak a (#2)", {"src/a.txt": "a2\n"})
        cls.c3 = f.commit("Carol", "carol@example.com", 10, "docs (#3)", {"docs/guide.md": "g\n"})
        cls.c4 = f.commit("Frank", "frank@example.com", 5, "sibling change without a number", {"src/other.txt": "o\n"})
        f.git("switch", "-q", "-c", "feature")
        cls.tip = f.commit("Dave", "dave@example.com", 2, "feature work",
                           {"src/a.txt": "a3\n", "src/new.txt": "n\n", "package-lock.json": "{}\n"})
        f.git("switch", "-q", "main")
        cls.c5 = f.commit("Eve", "eve@example.com", 1, "advance (#5)", {"src/a.txt": "a4\n"})
        cls.c6 = f.commit("dep-bot[bot]", "bot@example.com", 1, "bump (#6)",
                          {"src/a.txt": "a5\n", "package-lock.json": "{ }\n"})
        f.git("switch", "-q", "feature")
        cls.github = {
            "pr_view": None,
            "pulls": {
                "1": pull(1, user("alice-gh"), (user("bob-gh"), "APPROVED"), (user("dave-gh"), "APPROVED"),
                          (user("zed"), "COMMENTED")),
                "2": pull(2, user("bob-gh"), (user("alice-gh"), "CHANGES_REQUESTED"),
                          (bot("review-bot[bot]"), "APPROVED"), (user("bob-gh"), "APPROVED")),
                "5": pull(5, user("eve-gh")),
                "6": pull(6, bot("dep-bot[bot]"), (user("bob-gh"), "APPROVED")),
            },
            "commits": {
                cls.c4: {"login": "frank-gh", "pr": pull(4, user("frank-gh"), (user("grace-gh"), "APPROVED"))},
                cls.tip: {"login": "dave-gh", "pr": None},
            },
            "search": [pull(90, user("bob-gh"), (user("zed"), "APPROVED"), (user("dave-gh"), "APPROVED")),
                       pull(91, user("zed"), (user("yuri"), "APPROVED")),
                       pull(92, user("alice-gh"), (user("zed"), "APPROVED"))],
        }

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # --- arguments and errors ---

    def test_help(self):
        result = self.fx.run("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("usage: reviewers", result.stdout)

    def test_rejects_zero_limit(self):
        result = self.fx.run("-n", "0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive integer", result.stderr)

    def test_rejects_unknown_revision(self):
        result = self.fx.run("--no-github", "feature", "nope")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Unknown revision: nope", result.stderr)

    def test_requires_repository(self):
        with tempfile.TemporaryDirectory() as empty:
            result = self.fx.run("--no-github", cwd=empty)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Not a git repository", result.stderr)

    def test_reports_no_changes(self):
        result = self.fx.run("--no-github", "main", "main")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "No changes between main and main")

    # --- commit history only ---

    def test_git_only_ranking(self):
        result = self.fx.run("--no-github", "feature", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Changed: 2 files in 1 directory", result.stdout)
        self.assertIn("Excluded: Dave (change author), Tester (git user)", result.stdout)
        self.assertIn("ranking uses commit authorship only", result.stdout)
        table = rows(result.stdout)
        self.assertEqual([r["who"] for r in table], ["Eve", "Bob", "Frank", "Alice"])
        self.assertEqual([r["match"] for r in table], ["files", "files", "dirs", "files"])
        self.assertEqual(table[0]["score"], "100")
        self.assertTrue(all(r["reviewed"] == 0 and r["authored"] == 1 for r in table))
        self.assertNotIn("[bot]", result.stdout)
        self.assertNotIn("Carol", result.stdout)

    def test_since_window_drops_old_history(self):
        result = self.fx.run("--no-github", "--since", "100", "feature", "main")
        self.assertEqual([r["who"] for r in rows(result.stdout)], ["Eve", "Bob", "Frank"])

    def test_default_branch_and_base(self):
        result = self.fx.run("--no-github")
        self.assertIn("Suggested reviewers for: HEAD vs main", result.stdout)
        self.assertEqual(rows(result.stdout)[0]["who"], "Eve")

    def test_limit(self):
        result = self.fx.run("--no-github", "-n", "2", "feature", "main")
        self.assertEqual(len(rows(result.stdout)), 2)

    def test_missing_gh_is_reported(self):
        only_git = self.fx.root / "only-git"
        only_git.mkdir(exist_ok=True)
        link = only_git / "git"
        if not link.exists():
            link.symlink_to(shutil.which("git"))
        result = subprocess.run([sys.executable, str(SCRIPT), "feature", "main"], cwd=self.fx.repo,
                                capture_output=True, text=True, env={**self.fx.env, "PATH": str(only_git)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gh is not installed", result.stdout)
        self.assertEqual(rows(result.stdout)[0]["who"], "Eve")

    # --- with GitHub review history ---

    def test_github_ranking(self):
        result = self.fx.run("feature", "main", github=self.github)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Excluded: Tester (git user), dave-gh (change author)", result.stdout)
        table = rows(result.stdout)
        self.assertEqual([r["who"] for r in table], ["bob-gh", "alice-gh", "grace-gh", "eve-gh", "frank-gh"])
        by = {r["who"]: r for r in table}
        self.assertEqual((by["bob-gh"]["reviewed"], by["bob-gh"]["authored"]), (2, 1))
        self.assertEqual((by["alice-gh"]["reviewed"], by["alice-gh"]["authored"]), (1, 1))
        self.assertEqual((by["grace-gh"]["reviewed"], by["grace-gh"]["match"]), (1, "dirs"))
        self.assertEqual(by["eve-gh"]["reviewed"], 0)
        self.assertNotIn("zed", result.stdout, "a COMMENTED review is not review evidence")
        self.assertNotIn("[bot]", result.stdout)
        self.assertNotIn("Dave", result.stdout, "the change author resolves to one login")
        self.assertEqual(self.fx.log.read_text().count("api graphql"), 1, "one batched request")

    def test_exclude_flag(self):
        result = self.fx.run("--exclude", "bob-gh", "feature", "main", github=self.github)
        self.assertIn("bob-gh (excluded)", result.stdout)
        self.assertEqual(rows(result.stdout)[0]["who"], "alice-gh")

    def test_repository_wide_fallback_fills_remaining_slots(self):
        result = self.fx.run("-n", "8", "feature", "main", github=self.github)
        table = rows(result.stdout)
        self.assertEqual([(r["who"], r["match"], r["reviewed"]) for r in table[5:]],
                         [("zed", "repo", 2), ("yuri", "repo", 1)])
        self.assertTrue(all(r["score"] == "-" for r in table[5:]))
        self.assertNotIn("dave-gh", [r["who"] for r in table])

    def test_existing_pull_request_context(self):
        github = {**self.github, "pr_view": {
            "number": 7, "author": {"login": "dave-gh"}, "baseRefName": "main",
            "reviews": [{"author": {"login": "grace-gh"}, "state": "COMMENTED"}],
            "reviewRequests": [{"login": "bob-gh"}, {"name": "acme/widgets-team"}]}}
        result = self.fx.run("feature", github=github)
        self.assertIn("Suggested reviewers for: feature vs main", result.stdout)
        self.assertIn("Pull request #7: reviewed by grace-gh; requested: acme/widgets-team, bob-gh", result.stdout)
        self.assertIn("dave-gh (change author)", result.stdout)

    def test_gh_failure_degrades_to_commit_history(self):
        result = self.fx.run("feature", "main", github={**self.github, "fail": True})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GitHub review history unavailable: gh: simulated failure", result.stdout)
        self.assertEqual(rows(result.stdout)[0]["who"], "Eve")

    # --- evidence has to cover both signals ---

    def test_header_reports_how_much_evidence_carries_review_data(self):
        result = self.fx.run("feature", "main", github=self.github)
        self.assertIn("Ranked from: the 5 most relevant pull requests with review data, "
                      "100% of the weighted history on these paths", result.stdout)

    def test_unreviewed_pull_request_credits_nobody(self):
        """A pull request GitHub did not return may have had reviewers we cannot see, so scoring its
        author would rank authorship on coverage rather than on evidence."""
        github = {**self.github, "pulls": {k: v for k, v in self.github["pulls"].items() if k != "5"}}
        result = self.fx.run("feature", "main", github=github)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("eve-gh", result.stdout)
        self.assertNotIn("Eve", result.stdout)
        self.assertIn("Ranked from: the 4 most relevant pull requests", result.stdout)

    def test_no_review_data_at_all_degrades_to_authorship(self):
        github = {**self.github, "pulls": {}, "commits": {self.tip: {"login": "dave-gh", "pr": None}}}
        result = self.fx.run("-n", "4", "feature", "main", github=github)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ranking uses commit authorship only", result.stdout)
        self.assertNotIn("Ranked from:", result.stdout)
        self.assertEqual([r["who"] for r in rows(result.stdout)], ["Eve", "Bob", "Frank", "Alice"])

    def test_hash_lookups_reach_one_commit_per_author_first(self):
        self.fx.run("feature", "main", github=self.github)
        requested = re.findall(r'object\(oid: "([0-9a-f]+)"\)', self.fx.queries.read_text())
        self.assertIn(self.c4, requested, "Frank's only commit carries no pull request number")


class StaleLocalBaseTest(unittest.TestCase):
    """A worktree's local main lags behind; the remote-tracking ref must win."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="reviewers-stale.")
        f = self.fx = Fixture(self.tmp.name)
        f.commit("Alice", "alice@example.com", 40, "init (#1)", {"src/a.txt": "a\n"})
        f.git("branch", "stale-main")
        f.commit("Bob", "bob@example.com", 20, "newer main (#2)", {"src/b.txt": "b\n"})
        f.git("update-ref", "refs/remotes/origin/main", "HEAD")
        f.git("switch", "-q", "-c", "feature")
        f.commit("Carol", "carol@example.com", 1, "feature work", {"src/a.txt": "a2\n"})
        f.git("branch", "-f", "main", "stale-main")

    def tearDown(self):
        self.tmp.cleanup()

    def test_remote_tracking_base_wins_over_stale_local_main(self):
        result = self.fx.run("--no-github", "feature")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Suggested reviewers for: feature vs origin/main", result.stdout)
        self.assertIn("Changed: 1 file in 1 directory", result.stdout)
        self.assertIn("Excluded: Carol (change author)", result.stdout)
        self.assertNotIn("Bob (change author)", result.stdout)
        self.assertEqual([r["who"] for r in rows(result.stdout)], ["Alice", "Bob"], "same-file beats sibling")

    def test_explicit_stale_base_warns_about_many_authors(self):
        self.crowd_the_branch()
        result = self.fx.run("--no-github", "feature", "main")
        self.assertIn("Warning: 5 people authored commits between main and feature", result.stdout)
        self.assertIn("main is behind; fetch and pass origin/main", result.stdout)

    def test_no_warning_when_the_base_is_already_remote_tracking(self):
        """The old message computed a ref name from the base and told people to pass origin/HEAD~20."""
        self.crowd_the_branch()
        result = self.fx.run("--no-github", "feature", "origin/main")
        self.assertNotIn("Warning:", result.stdout)

    def test_no_warning_when_no_fresher_ref_exists(self):
        self.crowd_the_branch()
        result = self.fx.run("--no-github", "feature", "stale-main")
        self.assertNotIn("Warning:", result.stdout)

    def test_no_warning_for_a_base_that_is_a_revision_expression(self):
        """`origin/HEAD~4` resolves in any clone that has an origin/HEAD, so the fresher ref has to be
        matched as a ref rather than resolved as a revision."""
        self.crowd_the_branch()
        # origin/HEAD needs enough ancestors for `origin/HEAD~4` to resolve, as it would in a clone.
        self.fx.git("update-ref", "refs/remotes/origin/main", "feature")
        self.fx.git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        result = self.fx.run("--no-github", "feature", "HEAD~4")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("origin/HEAD~4", result.stdout)
        self.assertNotIn("Warning:", result.stdout)

    def crowd_the_branch(self):
        for i, who in enumerate(["Dan", "Erin", "Fay"]):
            self.fx.git("switch", "-q", "feature")
            self.fx.commit(who, f"{who.lower()}@example.com", 1, f"more {i}", {f"src/{who}.txt": "x\n"})


class LargeHistoryTest(unittest.TestCase):
    """More pull requests touch the paths than the ranker looks at. It takes the most relevant ones
    and says how much of the history that sample covers."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="reviewers-batch.")
        f = cls.fx = Fixture(cls.tmp.name)
        cls.pulls = {}
        for number in range(1, 61):
            f.commit(f"Author{number}", f"author{number}@example.com", 300 - number * 4,
                     f"change {number} (#{number})", {"src/a.txt": f"{number}\n"})
            cls.pulls[str(number)] = pull(number, user(f"author{number}-gh"), (user("owl"), "APPROVED"))
        f.git("switch", "-q", "-c", "feature")
        f.commit("Dev", "dev@example.com", 1, "the change", {"src/a.txt": "new\n"})

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_only_the_most_relevant_pull_requests_are_asked_about(self):
        result = self.fx.run("feature", "main", github={"pr_view": None, "pulls": self.pulls, "commits": {}})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.fx.log.read_text().count("api graphql"), 1, "one batched request")
        self.assertEqual(len(re.findall(r'pullRequest\(number:', self.fx.queries.read_text())), 50)
        self.assertRegex(result.stdout, r"Ranked from: the 50 most relevant pull requests with review data, "
                                        r"\d+% of the weighted history")
        self.assertEqual(rows(result.stdout)[0]["who"], "owl")


class SiblingWeightTest(unittest.TestCase):
    """A sibling file is worth a share of the changed files it sits beside, not a share of the
    directories. Dividing by the directory count made a sibling worth more as the change widened,
    and made every directory count the same however much of the change lived in it."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="reviewers-siblings.")
        f = self.fx = Fixture(self.tmp.name)
        f.commit("Root", "root@example.com", 300, "init",
                 {"busy/a.txt": "a\n", "busy/b.txt": "b\n", "busy/c.txt": "c\n", "quiet/a.txt": "a\n"})
        # Same age, same number of commits: only which directory they touched differs.
        f.commit("Busy", "busy@example.com", 30, "sibling of three changed files", {"busy/z.txt": "z\n"})
        f.commit("Quiet", "quiet@example.com", 30, "sibling of one changed file", {"quiet/z.txt": "z\n"})
        f.git("switch", "-q", "-c", "feature")
        f.commit("Dev", "dev@example.com", 1, "the change",
                 {"busy/a.txt": "a2\n", "busy/b.txt": "b2\n", "busy/c.txt": "c2\n", "quiet/a.txt": "a2\n"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_sibling_weight_follows_the_changed_files_in_the_directory(self):
        result = self.fx.run("--no-github", "feature", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        table = {r["who"]: r for r in rows(result.stdout)}
        self.assertEqual(table["Busy"]["score"], "100")
        self.assertEqual(table["Quiet"]["score"], "33", "one changed file against three")
        self.assertEqual([table["Busy"]["match"], table["Quiet"]["match"]], ["dirs", "dirs"])


class UncommittedChangesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="reviewers-dirty.")
        f = self.fx = Fixture(self.tmp.name)
        f.commit("Alice", "alice@example.com", 40, "init (#1)", {"src/a.txt": "a\n"})
        f.commit("Bob", "bob@example.com", 20, "more (#2)", {"src/b.txt": "b\n"})
        (f.repo / "src" / "a.txt").write_text("edited\n")
        (f.repo / "src" / "brand-new.txt").write_text("new\n")

    def tearDown(self):
        self.tmp.cleanup()

    def test_ranks_the_working_tree_when_nothing_is_committed_yet(self):
        result = self.fx.run("--no-github")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("uncommitted changes; nothing is committed on this branch yet", result.stdout)
        self.assertIn("Changed: 2 files in 1 directory", result.stdout, "an untracked file counts too")
        self.assertEqual([r["who"] for r in rows(result.stdout)], ["Alice", "Bob"])

    def test_committed_work_wins_over_the_working_tree(self):
        self.fx.git("switch", "-q", "-c", "feature")
        self.fx.commit("Dev", "dev@example.com", 1, "real work", {"src/b.txt": "b2\n"})
        result = self.fx.run("--no-github", "feature", "main")
        self.assertNotIn("uncommitted", result.stdout)
        self.assertIn("Changed: 1 file in 1 directory", result.stdout)


class MergeCommitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="reviewers-merge.")
        f = self.fx = Fixture(self.tmp.name)
        f.commit("Alice", "alice@example.com", 40, "init (#1)", {"src/a.txt": "a\n"})
        f.git("switch", "-q", "-c", "topic")
        f.commit("Bob", "bob@example.com", 30, "add b", {"src/b.txt": "b\n"})
        f.git("switch", "-q", "main")
        self.merge = f.commit("Merger", "merger@example.com", 29, "Merge pull request #2 from bob/topic", merge="topic")
        f.git("switch", "-q", "-c", "feature")
        self.tip = f.commit("Carol", "carol@example.com", 1, "add c", {"src/c.txt": "c\n"})

    def tearDown(self):
        self.tmp.cleanup()

    def test_merge_commit_files_count_and_git_only_attributes_to_merger(self):
        result = self.fx.run("--no-github", "feature", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("History: 2 commits", result.stdout)
        self.assertEqual([r["who"] for r in rows(result.stdout)], ["Merger", "Alice"])

    def test_merge_commit_attributes_to_pull_request_author_with_github(self):
        github = {"pr_view": None,
                  "pulls": {"2": pull(2, user("bob-gh"), (user("alice-gh"), "APPROVED"))},
                  "commits": {self.tip: {"login": "carol-gh", "pr": None}}}
        result = self.fx.run("feature", "main", github=github)
        self.assertEqual(result.returncode, 0, result.stderr)
        table = rows(result.stdout)
        self.assertEqual([r["who"] for r in table], ["alice-gh", "bob-gh"])
        self.assertEqual(table[0]["reviewed"], 1)
        self.assertNotIn("merger", result.stdout.lower())
        self.assertNotIn("Alice", result.stdout,
                         "commit #1 has no review data, so its author is not evidence either")


if __name__ == "__main__":
    unittest.main(verbosity=1)
