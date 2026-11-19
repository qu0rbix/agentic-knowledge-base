"""Guard and capture hooks, replayed with recorded hook JSON (no model)."""
import json
import re
import unittest

from helpers import TODAY, bash, commit, git, hook, make_kb, note, put, run_kb, source, write_tool

POLICY = "Production changes need 2 approvals from the Data Platform team."


class GuardPre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kb = make_kb()

    def code(self, payload):
        return hook(self.kb, "pre", payload).returncode

    def test_main_writes_notes_and_own_tools(self):
        self.assertEqual(self.code(write_tool("notes/x.md")), 0)
        self.assertEqual(self.code(write_tool("tools/portwatch.py")), 0)

    def test_scaffold_and_owner_files_need_the_file_tools(self):
        self.assertEqual(self.code(write_tool("tools/kb.py", "reviewer")), 2)
        self.assertEqual(self.code(bash("echo x > tools/hooks/guard.py")), 2)
        self.assertEqual(self.code(bash("Set-Content -Path charter.md -Value x", tool="PowerShell")), 2)

    def test_agent_cannot_write_sources_user(self):
        for role in (None, "reviewer"):
            self.assertEqual(self.code(write_tool("sources/user/2026-11-13-x.md", role)), 2, role)

    def test_reviewer_writes_audits(self):
        self.assertEqual(self.code(write_tool("meta/audits/x-review.md", "reviewer")), 0)

    def test_harmless_commands_allowed(self):
        cmds = [
            'uv run tools/kb.py search "touch points"',
            'uv run tools/kb.py search "how do we mv containers"',
            "uv run tools/kb.py check 2>&1 | tee work/check.txt",
            "mkdir -p work/q && uv run tools/fetch.py https://example.com --slug x",
            "uv run tools/kb.py stats && rm work/tmp.csv",
            "mv data/old.csv data/archive/old.csv",
            "cp notes/vendor-x.md work/scratch.md",
            "python -c \"print(open('notes/a.md').read())\"",
            "grep -c src notes/*.md && touch work/done",
            "uv run python work/q.py > work/out.csv",
        ]
        blocked = [c for c in cmds if self.code(bash(c)) != 0]
        self.assertEqual(blocked, [])

    def test_redirect_into_owner_files_blocked_bash_and_powershell(self):
        self.assertEqual(self.code(bash("echo x > kb.toml")), 2)
        self.assertEqual(self.code(bash("echo x > CLAUDE.md", tool="PowerShell")), 2)
        self.assertEqual(self.code(bash("uv run tools/kb.py new topic x --title t --summary s")), 0)

    def test_malformed_input_blocks(self):
        import subprocess, sys
        r = subprocess.run([sys.executable, "-I", str(self.kb / "tools/hooks/guard.py"), "pre"], input="not json",
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)


class GuardPost(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()
        source(self.kb, "2026-09-29-policy", POLICY)
        note(self.kb, "change-approval", [f'Changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        commit(self.kb)
        hook(self.kb, "manifest", {})

    def test_script_write_is_violation_until_restored(self):
        p = self.kb / "charter.md"
        orig = p.read_text(encoding="utf-8")
        p.write_text(orig + "\n- injected\n", encoding="utf-8", newline="\n")
        self.assertEqual(hook(self.kb, "post", bash("uv run python work/x.py")).returncode, 2)
        self.assertIn("changed by role 'main'", run_kb(self.kb, "check").stdout)
        p.write_text(orig, encoding="utf-8", newline="\n")
        self.assertNotIn("changed by role", run_kb(self.kb, "check").stdout)

    def test_restored_violation_then_librarian_edit(self):
        p = self.kb / "charter.md"
        orig = p.read_text(encoding="utf-8")
        p.write_text(orig + "\n- injected\n", encoding="utf-8", newline="\n")
        hook(self.kb, "post", bash("uv run python work/x.py"))
        p.write_text(orig, encoding="utf-8", newline="\n")
        run_kb(self.kb, "check")
        p.write_text(orig.replace("Changes need", "Production changes need"), encoding="utf-8", newline="\n")
        self.assertEqual(hook(self.kb, "post", write_tool(str(p), "librarian", "Edit")).returncode, 0)
        self.assertNotIn("changed by role", run_kb(self.kb, "check").stdout)

    def test_librarian_post_refreshes_manifest(self):
        p = put(self.kb, "notes/new-note.md", "x")
        hook(self.kb, "post", write_tool(str(p), "librarian"))
        # a later main-agent command must not see the librarian's file as a violation
        self.assertEqual(hook(self.kb, "post", bash("ls")).returncode, 0)

    def test_shell_cannot_edit_charter(self):
        p = self.kb / "charter.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nAnything goes.\n", encoding="utf-8", newline="\n")
        self.assertEqual(hook(self.kb, "post", bash("sed -i s/a/b/ charter.md")).returncode, 2)

    def test_edit_tool_on_charter_is_accepted(self):
        p = self.kb / "charter.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nScope: X.\n", encoding="utf-8", newline="\n")
        self.assertEqual(hook(self.kb, "post", write_tool(str(p), None, "Edit")).returncode, 0)
        self.assertEqual(hook(self.kb, "post", bash("ls")).returncode, 0)

    def test_heartbeat_required_under_claudecode(self):
        out = run_kb(self.kb, "check", env={"CLAUDECODE": "1"}).stdout
        self.assertIn("heartbeat", out)
        hook(self.kb, "pre", bash("ls"))
        out = run_kb(self.kb, "check", env={"CLAUDECODE": "1"}).stdout
        self.assertNotIn("heartbeat", out)


class CommitGate(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()
        source(self.kb, "2026-09-29-policy", POLICY + " Approvers rotate weekly.")
        note(self.kb, "change-approval", [f'Changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        note(self.kb, "rotation", ['Approvers rotate weekly. [src: 2026-09-29-policy §1 "Approvers rotate weekly"]'])
        commit(self.kb)

    def digest(self):
        return re.search(r"digest: (\w+)", run_kb(self.kb, "precheck").stdout).group(1)

    def gate(self):
        r = run_kb(self.kb, "commit", "-m", "kb: x")
        return 0 if r.returncode == 0 else 2

    def test_default_commit_needs_only_a_clean_check(self):
        p = self.kb / "notes/rotation.md"
        p.write_text(p.read_text(encoding="utf-8") + "- Approvers rotate on Mondays. [src: 2026-09-29-policy §1 \"Approvers rotate weekly\"]\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.gate(), 0)

    def test_commit_blocked_without_review_then_allowed_then_blocked_again(self):
        t = self.kb / "kb.toml"
        t.write_text(t.read_text(encoding="utf-8").replace('mode = "audit"', 'mode = "always"'), encoding="utf-8", newline="\n")
        commit(self.kb)
        p = self.kb / "notes/change-approval.md"
        p.write_text(p.read_text(encoding="utf-8").replace("Changes need", "Production changes need"), encoding="utf-8", newline="\n")
        put(self.kb, "history/change-approval.md",
            f'## Superseded {TODAY}\n- Changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]\nreason: rewording\n')
        self.assertEqual(self.gate(), 2)
        put(self.kb, f"meta/audits/{TODAY}-120000-review.md", f"Digest: {self.digest()}\nVerdict: approved\n")
        before = len(git(self.kb, "log", "--oneline").stdout.splitlines())
        self.assertEqual(self.gate(), 0)
        self.assertEqual(len(git(self.kb, "log", "--oneline").stdout.splitlines()), before + 1)
        p.write_text(p.read_text(encoding="utf-8") + "- Late edit. [src: 2026-09-29-policy §1 \"Approvers rotate weekly\"]\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.gate(), 2)

    def test_pure_move_commits_without_review(self):
        (self.kb / "notes/sub").mkdir()
        (self.kb / "notes/rotation.md").rename(self.kb / "notes/sub/rotation.md")
        self.assertIn("review: skip", run_kb(self.kb, "precheck").stdout)
        self.assertEqual(self.gate(), 0)

    def test_cross_note_move_needs_review(self):
        a, b = self.kb / "notes/change-approval.md", self.kb / "notes/rotation.md"
        line = [l for l in a.read_text(encoding="utf-8").splitlines() if l.startswith("- ")][0]
        a.write_text(a.read_text(encoding="utf-8").replace(line + "\n", ""), encoding="utf-8", newline="\n")
        b.write_text(b.read_text(encoding="utf-8") + line + "\n", encoding="utf-8", newline="\n")
        self.assertIn("review: required", run_kb(self.kb, "precheck").stdout)


class Capture(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()

    def test_every_prompt_saved_and_same_day_statements_citable(self):
        hook(self.kb, "prompt", {"prompt": "Exec briefs must be one page, never longer."}, "capture.py")
        note(self.kb, "brief-format", [f'Exec briefs are one page. [src: user {TODAY} "Exec briefs must be one page"]'], ntype="preference")
        self.assertRegex(run_kb(self.kb, "check").stdout, r"(?m)^0 problem")
        commit(self.kb)
        hook(self.kb, "prompt", {"prompt": "Status reports go to Dana Smit every Friday."}, "capture.py")
        note(self.kb, "status-reports", [f'Status reports go to Dana Smit weekly. [src: user {TODAY} "Status reports go to Dana Smit"]'], ntype="preference")
        out = run_kb(self.kb, "check").stdout
        self.assertRegex(out, r"(?m)^0 problem", out)
        self.assertEqual(len(list((self.kb / "sources/user").glob(f"{TODAY}-*.md"))), 2)

    def test_fabricated_owner_quote_fails(self):
        hook(self.kb, "prompt", {"prompt": "Use tables in reports."}, "capture.py")
        note(self.kb, "x", [f'Owner wants charts. [src: user {TODAY} "always use charts in reports"]'], ntype="preference")
        self.assertIn("owner quote not found", run_kb(self.kb, "check").stdout)

    def _prompt(self, text, session="s1"):
        r = hook(self.kb, "prompt", {"prompt": text, "session_id": session}, "capture.py")
        ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
        return re.search(r"sources/user/(\S+)\.md", ctx).group(1), ctx

    def _stop(self, session="s1", active=False):
        r = hook(self.kb, "stop", {"session_id": session, "stop_hook_active": active}, "capture.py")
        return json.loads(r.stdout) if r.stdout.strip() else None

    def test_every_message_gets_a_language_free_reminder(self):
        mid, ctx = self._prompt("Das stimmt so nicht mehr: Jonas hat Fivewire übernommen.")
        self.assertIn("whatever language", ctx)
        self.assertIn(mid, ctx)

    def test_uncited_recent_messages_listed_at_session_start(self):
        mid, _ = self._prompt("btw Jonas took over the Fivewire contract last week")
        self.assertIn("Jonas took over", run_kb(self.kb, "stats").stdout)
        note(self.kb, "fivewire", [f'Jonas owns the Fivewire contract. [src: user {TODAY} "Jonas took over the Fivewire contract"]'])
        self.assertNotIn("Jonas took over", run_kb(self.kb, "stats").stdout)

    def test_no_stop_hook(self):
        import json as _j
        st = _j.loads((self.kb / ".claude/settings.json").read_text(encoding="utf-8"))
        self.assertNotIn("Stop", st["hooks"])

    def test_kb_commit_keeps_uncited_owner_messages_out_of_git(self):
        aside, _ = self._prompt("my private aside about Zanzibar")
        cited, _ = self._prompt("From now on briefs are one page at most.")
        note(self.kb, "briefs", [f'Briefs are one page at most. [src: user {TODAY} "briefs are one page at most"]'])
        git(self.kb, "add", "-A")  # an agent's or owner's `git add -A` does not pick up owner messages
        self.assertNotIn(aside, git(self.kb, "diff", "--cached", "--name-only").stdout)
        dig = re.search(r"digest: (\w+)", run_kb(self.kb, "precheck").stdout).group(1)
        put(self.kb, "meta/audits/r.md", f"Digest: {dig}\nVerdict: approved\n")
        out = run_kb(self.kb, "commit", "-m", "kb: briefs")
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        tracked = git(self.kb, "ls-files", "sources/user").stdout
        self.assertIn(cited, tracked)
        self.assertNotIn(aside, tracked)

    def test_raw_git_commit_refused(self):
        for cmd in ("git commit -m x", "git add -A && git commit -m x", "git -c a=b commit"):
            self.assertEqual(hook(self.kb, "pre", bash(cmd)).returncode, 2, cmd)
        self.assertEqual(hook(self.kb, "pre", bash('uv run tools/kb.py search "git commit policy"')).returncode, 0)

class Settings(unittest.TestCase):
    def test_powershell_and_fail_closed(self):
        from helpers import TEMPLATE
        s = json.loads((TEMPLATE / ".claude/settings.json").read_text(encoding="utf-8"))
        pre = s["hooks"]["PreToolUse"][0]
        self.assertIn("PowerShell", pre["matcher"])
        self.assertEqual(pre["hooks"][0].get("onFailure"), "block")
        self.assertIn("PowerShell", s["hooks"]["PostToolUse"][0]["matcher"])
        self.assertEqual(s.get("env", {}).get("CLAUDE_CODE_FORK_SUBAGENT"), "0")
        self.assertIn("fork", s["hooks"]["SessionStart"][0]["matcher"])
        self.assertTrue(any(r.startswith("PowerShell(") for r in s["permissions"]["allow"]))


if __name__ == "__main__":
    unittest.main()
