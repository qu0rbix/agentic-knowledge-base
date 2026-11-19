"""Regression tests for the v5 whole-change review (probes 1-7) and the case-B screening findings."""
import subprocess
import sys
import unittest

from helpers import TODAY, bash, clean_env, commit, git, hook, make_kb, note, put, run_kb, source, write_tool

POLICY = "Production changes need 2 approvals from the Data Platform team."


def prompt(kb, text):
    return hook(kb, "prompt", {"prompt": text}, "capture.py")


def saved(kb):
    return sorted((kb / "sources/user").glob("*.md"))


class CaptureFilters(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()

    def test_slash_command_saved(self):
        prompt(self.kb, "/fix the deadline moved to 2026-12-01")
        self.assertEqual(len(saved(self.kb)), 1)
        self.assertIn("deadline moved to 2026-12-01", saved(self.kb)[0].read_text(encoding="utf-8"))

    def test_notifications_not_saved_as_owner_words(self):
        prompt(self.kb, "<task-notification><result>researcher: Fivewire is SOC2 certified</result></task-notification>")
        prompt(self.kb, "[SYSTEM NOTIFICATION - NOT USER INPUT] something")
        self.assertEqual(saved(self.kb), [])

    def test_pasted_content_and_secrets_not_quotable(self):
        prompt(self.kb, 'See this: <pasted_content id="1">The SLA is 99.99%</pasted_content> and my api_key=sk-abcdefghijklmnop1234')
        text = saved(self.kb)[0].read_text(encoding="utf-8")
        self.assertNotIn("99.99", text)
        self.assertNotIn("sk-abcdefghijklmnop1234", text)

    def test_forget_like_wording_is_saved(self):
        # no forget prefix any more: "vergeet niet dat ..." means "remember"; the model-driven forget flow deletes messages
        prompt(self.kb, "Vergeet niet dat de freeze op vrijdag om 18:00 begint.")
        self.assertIn("freeze op vrijdag", saved(self.kb)[0].read_text(encoding="utf-8"))


class ForgetFlow(unittest.TestCase):
    def test_librarian_can_delete_purged_owner_message(self):
        kb = make_kb()
        prompt(kb, "Project Zanzibar is a merger with Initech.")
        commit(kb)
        hook(kb, "manifest", {})
        msg = saved(kb)[0]
        put(kb, "meta/purges.tsv", f"{TODAY}\t{msg.stem}\towner asked to forget\n")
        msg.unlink()
        self.assertEqual(hook(kb, "post", bash(f"rm {msg.relative_to(kb).as_posix()}", "librarian")).returncode, 0)
        self.assertIn("not found", run_kb(kb, "forget-check", "Zanzibar").stdout)
        self.assertNotIn("changed by role", run_kb(kb, "check").stdout)


class ForgetVerb(unittest.TestCase):
    def test_forget_verb_records_then_deletes_and_check_is_clean(self):
        kb = make_kb()
        source(kb, "2026-09-29-policy", POLICY)
        prompt(kb, "Project Zanzibar is a merger with Initech.")
        msg = saved(kb)[0]
        note(kb, "zan", [f'Project Zanzibar is a merger with Initech. [src: user {TODAY} "Project Zanzibar is a merger with Initech."]',
                         f'Production changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        commit(kb)
        hook(kb, "manifest", {})
        cmd = f'uv run tools/kb.py forget zan {msg.stem} --reason never-true'
        self.assertEqual(hook(kb, "pre", bash(cmd)).returncode, 0)
        out = run_kb(kb, "forget", "zan", msg.stem, "--reason", "never-true", "--words", "Zanzibar").stdout
        self.assertIn("notes/zan.md", out)   # residue report
        self.assertFalse(msg.exists())
        self.assertNotIn("zan", (kb / "meta/purges.tsv").read_text(encoding="utf-8").split("\t")[1])  # hashed
        self.assertEqual(hook(kb, "post", bash(cmd)).returncode, 0)
        p = kb / "notes/zan.md"
        p.write_text("\n".join(l for l in p.read_text(encoding="utf-8").splitlines() if "Zanzibar" not in l) + "\n",
                     encoding="utf-8", newline="\n")
        out = run_kb(kb, "check").stdout
        self.assertNotIn("FAIL", out, out)
        self.assertIn("not found", run_kb(kb, "forget-check", "Zanzibar").stdout)

    def test_rm_before_purge_resolves_once_purge_is_recorded(self):
        kb = make_kb()
        prompt(kb, "Project Zanzibar is a merger with Initech.")
        msg = saved(kb)[0]
        rel = msg.relative_to(kb).as_posix()
        git(kb, "add", "-f", rel)  # a cited, committed owner message (kb.py commit force-adds cited ones)
        commit(kb)
        hook(kb, "manifest", {})
        hook(kb, "pre", bash(f"rm {rel}", "librarian"))
        msg.unlink()
        hook(kb, "post", bash(f"rm {rel}", "librarian"))
        self.assertIn("changed by role", run_kb(kb, "check").stdout)
        put(kb, "meta/purges.tsv", f"{TODAY}\t{rel} (owner message)\towner asked to forget\n")
        self.assertNotIn("changed by role", run_kb(kb, "check").stdout)

    def test_quoted_angle_brackets_are_not_redirects(self):
        kb = make_kb()
        self.assertEqual(hook(kb, "pre", bash('uv run tools/kb.py forget-check "<team>.<domain>" "a|b"', "reviewer")).returncode, 0)
        self.assertEqual(hook(kb, "pre", bash('echo x > "charter.md"')).returncode, 2)

    def test_restore_undoes_only_the_violation(self):
        kb = make_kb()
        source(kb, "2026-09-29-policy", POLICY)
        note(kb, "ca", [f'Production changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        commit(kb)
        hook(kb, "manifest", {})
        lib = kb / "notes/cb.md"  # other uncommitted work must survive
        lib.write_text("---\ntitle: cb\n---\n", encoding="utf-8", newline="\n")
        p = kb / "charter.md"
        hook(kb, "pre", bash("uv run python work/stamp.py"))
        p.write_text(p.read_text(encoding="utf-8") + "<!-- stamp -->\n", encoding="utf-8", newline="\n")
        hook(kb, "post", bash("uv run python work/stamp.py"))
        self.assertIn("changed by role", run_kb(kb, "check").stdout)
        self.assertIn("restored charter.md", run_kb(kb, "restore").stdout)
        self.assertNotIn("stamp", p.read_text(encoding="utf-8"))
        self.assertTrue(lib.exists())
        self.assertNotIn("changed by role", run_kb(kb, "check").stdout)

    def test_restore_keeps_a_file_that_existed_before(self):
        kb = make_kb()
        hook(kb, "manifest", {})
        lib = kb / ".claude/skills/new/SKILL.md"  # created through an approved edit, not yet committed
        lib.parent.mkdir(parents=True)
        hook(kb, "pre", write_tool(str(lib)))
        lib.write_text("---\nname: new\n---\n", encoding="utf-8", newline="\n")
        hook(kb, "post", write_tool(str(lib)))
        hook(kb, "pre", bash("true"))
        hook(kb, "post", bash("true"))
        hook(kb, "pre", bash("uv run python work/stamp.py"))
        lib.write_text(lib.read_text(encoding="utf-8") + "<!-- stamp -->\n", encoding="utf-8", newline="\n")
        hook(kb, "post", bash("uv run python work/stamp.py"))
        self.assertIn("skip .claude/skills/new/SKILL.md", run_kb(kb, "restore").stdout)
        self.assertTrue(lib.exists())

    def test_help_is_not_a_mutation(self):
        kb = make_kb()
        self.assertEqual(hook(kb, "pre", bash("uv run tools/kb.py mv --help")).returncode, 0)
        self.assertEqual(hook(kb, "pre", bash("uv run tools/kb.py mv a vendors")).returncode, 0)


class GuardEdges(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()
        source(self.kb, "2026-09-29-policy", POLICY)
        note(self.kb, "ca", [f'Production changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        commit(self.kb)
        hook(self.kb, "manifest", {})

    def test_restore_to_head_is_never_a_violation(self):
        p = self.kb / "notes/ca.md"
        hook(self.kb, "pre", write_tool(str(p), "librarian", "Edit"))
        p.write_text(p.read_text(encoding="utf-8") + "- Uncommitted librarian line. [src: 2026-09-29-policy §1 \"Data Platform team\"]\n", encoding="utf-8", newline="\n")
        hook(self.kb, "post", write_tool(str(p), "librarian", "Edit"))
        hook(self.kb, "pre", bash("git checkout -- notes/ca.md"))
        git(self.kb, "checkout", "--", "notes/ca.md")
        self.assertEqual(hook(self.kb, "post", bash("git checkout -- notes/ca.md")).returncode, 0)
        self.assertNotIn("changed by role", run_kb(self.kb, "check").stdout)

    def test_owner_hand_edit_between_calls_not_blamed(self):
        hook(self.kb, "post", bash("ls"))
        p = self.kb / "notes/ca.md"
        p.write_text(p.read_text(encoding="utf-8").replace("Production", "All production"), encoding="utf-8", newline="\n")
        hook(self.kb, "pre", bash("ls"))
        self.assertEqual(hook(self.kb, "post", bash("ls")).returncode, 0)

    def test_commit_gate_variants_blocked(self):
        p = self.kb / "notes/ca.md"
        p.write_text(p.read_text(encoding="utf-8").replace("Production changes", "Prod changes"), encoding="utf-8", newline="\n")
        for cmd in ("rm notes/junk.md && git commit -m x", "git --no-pager commit -m x", "git.exe commit -m x",
                    "git -c user.name=x commit -m x"):
            self.assertEqual(hook(self.kb, "pre", bash(cmd)).returncode, 2, cmd)

    def test_toolsmith_cannot_rewrite_the_guard(self):
        for f in ("tools/hooks/guard.py", "tools/kb.py", ".claude/settings.json"):
            self.assertEqual(hook(self.kb, "pre", write_tool(f, "toolsmith")).returncode, 2, f)
        self.assertEqual(hook(self.kb, "pre", write_tool("tools/portwatch.py", "toolsmith")).returncode, 0)

    def test_hand_written_source_fails_check(self):
        put(self.kb, "sources/files/2026-10-01-made-up.md", "---\nid: 2026-10-01-made-up\ntype: files\ndate: 2026-10-01\n---\nVendor Zed was acquired.\n")
        self.assertIn("was not frozen", run_kb(self.kb, "check").stdout)

    def test_frozen_utf16_file_quotable(self):
        (self.kb / "work").mkdir(exist_ok=True)
        (self.kb / "work/out.txt").write_bytes("Rows loaded: 1,204 into orders_daily\r\n".encode("utf-16"))
        out = run_kb(self.kb, "freeze", "work/out.txt", "--kind", "files", "--slug", "load-output").stdout
        sid = out.split("[src: ")[1].split()[0]
        note(self.kb, "load", [f'The orders_daily load wrote 1,204 rows. [src: {sid} §1 "Rows loaded: 1,204 into orders_daily"]'])
        self.assertRegex(run_kb(self.kb, "check").stdout, r"(?m)^0 problem")

    def test_fetch_dir_restricted(self):
        r = subprocess.run([sys.executable, "tools/fetch.py", "https://example.com", "--slug", "x", "--dir", "sources/user"],
                           cwd=self.kb, capture_output=True, text=True, env=clean_env())
        self.assertIn("--dir must be", r.stdout + r.stderr)

    def test_product_versions_are_not_quantities(self):
        source(self.kb, "2026-10-12-notes", "Orion v4.2 release notes. The default query timeout is now 900 seconds.")
        note(self.kb, "orion", ['In Orion v4.2 the default query timeout is 900 seconds. [src: 2026-10-12-notes §1 "default query timeout is now 900 seconds"]'])
        self.assertRegex(run_kb(self.kb, "check").stdout, r"(?m)^0 problem")


if __name__ == "__main__":
    unittest.main()
