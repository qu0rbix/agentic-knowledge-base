"""SQL-table notes: footnote citations, verbatim example blocks, the blank-line hole, history evidence (Fable review 4)."""
import unittest

from helpers import TODAY, commit, git, hook, make_kb, put, run_kb, source

DESCRIBE = "column | type\naccount_id | bigint\ncustomer_id | bigint\nstatus | smallint"
QUERY = "SELECT status, count(*) FROM table_x GROUP BY status;\nstatus | count\n2 | 3907\n9 | 1204"


def table_note(kb, body):
    put(kb, "notes/table-x.md", f"---\nid: table-x\ntype: dataset\ntitle: Table x\nsummary: Accounts table\nstatus: current\nupdated: 2026-10-01\n---\n{body}")


class Footnotes(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()
        source(self.kb, "2026-10-01-schema-table-x", DESCRIBE)
        source(self.kb, "2026-10-01-query-status-counts", QUERY)

    def check(self):
        return run_kb(self.kb, "check").stdout

    def test_footnoted_note_is_clean_and_numbers_still_checked(self):
        table_note(self.kb, "## Gotchas\n- Status 9 rows (1204 as of 2026-10-01) are soft-deleted. [^q]\n\n"
                            "## Sources\n[^q]: [src: 2026-10-01-query-status-counts §1 \"2 | 3907 9 | 1204\"]\n")
        self.assertRegex(self.check(), r"(?m)^0 problem")
        table_note(self.kb, "## Gotchas\n- Status 9 rows (1999) are soft-deleted. [^q]\n\n"
                            "## Sources\n[^q]: [src: 2026-10-01-query-status-counts §1 \"2 | 3907 9 | 1204\"]\n")
        self.assertIn("1999", self.check())

    def test_missing_and_unused_footnotes_fail(self):
        table_note(self.kb, "- Status 9 means soft-deleted. [^nope]\n\n## Sources\n[^q]: [src: 2026-10-01-query-status-counts §1 \"2 | 3907 9 | 1204\"]\n")
        out = self.check()
        self.assertIn("MISSING-FOOTNOTE", out)
        self.assertIn("[^q] is not used", out)

    def test_example_must_be_verbatim(self):
        ok = ("## Examples\n- Rows per status, as the soft-delete check uses. [^q]\n  ```sql\n  SELECT status, count(*) FROM table_x GROUP BY status;\n  ```\n\n"
              "## Sources\n[^q]: [src: 2026-10-01-query-status-counts §1 \"SELECT status, count(*) FROM table_x\"]\n")
        table_note(self.kb, ok)
        self.assertRegex(self.check(), r"(?m)^0 problem")
        table_note(self.kb, ok.replace("GROUP BY status;\n  ```", "WHERE status <> 9 GROUP BY status;\n  ```"))
        self.assertIn("not verbatim", self.check())

    def test_blank_line_ends_a_bullet(self):
        table_note(self.kb, "- Status 9 means soft-deleted. [src: 2026-10-01-query-status-counts §1 \"2 | 3907 9 | 1204\"]\n\n"
                            "  Join on customer_id, it is unique.\n")
        self.assertIn("text outside a claim bullet", self.check())

    def test_history_bullet_needs_inline_citation(self):
        put(self.kb, "history/table-x.md", f"## Superseded {TODAY}\n- Status 9 means archived. [^q]\nreason: changed - x\n")
        self.assertIn("superseded bullet without an inline", self.check())


class CitedSources(unittest.TestCase):
    def test_cited_source_is_not_labelled_raw(self):
        kb = make_kb()
        source(kb, "2026-10-01-schema-table-x", DESCRIBE)
        source(kb, "2026-10-02-misc-dump", "status smallint appears in an unrelated dump")
        table_note(kb, "## Schema\n- The full schema of table x is in the frozen describe output. "
                       "[src: 2026-10-01-schema-table-x §1 \"customer_id | bigint\"]\n")
        out = run_kb(kb, "search", "status smallint", "--in", "sources", "--keyword").stdout
        self.assertIn("SOURCE cited by notes/table-x", out)
        self.assertIn("RAW - not reviewed", out)


class Friendliness(unittest.TestCase):
    def test_stats_reports_unfinished_filing_and_outside_commits(self):
        kb = make_kb()
        source(kb, "2026-10-01-schema-table-x", DESCRIBE)
        table_note(kb, "- Table x is keyed by account_id. [src: 2026-10-01-schema-table-x §1 \"account_id | bigint\"]\n")
        out = run_kb(kb, "stats").stdout
        self.assertIn("uncommitted KB file", out)
        git(kb, "add", "-A")
        git(kb, "commit", "-qm", "owner quick fix")
        self.assertIn("owner quick fix", run_kb(kb, "stats").stdout)

    def test_freeze_a_pasted_owner_message(self):
        kb = make_kb()
        hook(kb, "prompt", {"prompt": "Here is the output:\ncolumn | type\naccount_id | bigint\nstatus | smallint"}, "capture.py")
        msg = sorted((kb / "sources/user").glob("*.md"))[0]
        out = run_kb(kb, "freeze", msg.relative_to(kb).as_posix(), "--kind", "files", "--slug", "schema-table-x").stdout
        sid = out.split("[src: ")[1].split()[0]
        frozen = next(kb.glob(f"sources/files/{sid}.md")).read_text(encoding="utf-8")
        self.assertIn("account_id | bigint", frozen)
        self.assertNotIn("type: user", frozen)


if __name__ == "__main__":
    unittest.main()
