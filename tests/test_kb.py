"""kb.py evidence, history, freshness, search and config checks."""
import sys
import unittest

from helpers import TEMPLATE, TODAY, commit, make_kb, note, put, run_kb, source

POLICY = "Production changes need 2 approvals from the Data Platform team."
LIMITS = "The batch API Alpha is limited to 4,000 req/s. The interactive API Beta allows 500 req/s."


class Evidence(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()
        source(self.kb, "2026-09-29-policy", POLICY)
        source(self.kb, "2026-09-30-limits", LIMITS)

    def check(self):
        return run_kb(self.kb, "check").stdout

    def test_clean_template(self):
        self.assertRegex(run_kb(make_kb(), "check").stdout, r"(?m)^0 problem")

    def test_source_citation_needs_no_quote_owner_citation_does(self):
        note(self.kb, "zed", ["Changes need approvals from the Data Platform team. [src: 2026-09-29-policy §1]"])
        self.assertRegex(self.check(), r"(?m)^0 problem")
        note(self.kb, "zed", ['Changes need approvals. [src: 2026-09-29-policy §1 "this sentence is not in the policy"]'])
        self.assertIn("quote not found", self.check())  # a quote that is given must be exact
        note(self.kb, "zed", ["Approvers rotate weekly. [src: user 2026-09-29]"])
        self.assertIn("needs the owner's words", self.check())

    def test_number_not_in_quote_fails(self):
        note(self.kb, "ca", ['Changes need 3 approvals. [src: 2026-09-29-policy §1 "need 2 approvals from the Data Platform"]'])
        self.assertIn("not in any cited source", self.check())
        note(self.kb, "ca", ["Changes need 3 approvals. [src: 2026-09-29-policy §1]"])  # no quote: checked against the source
        self.assertIn("not in any cited source", self.check())
        note(self.kb, "ca", ["Changes need 2 approvals. [src: 2026-09-29-policy §1]"])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_identifiers_are_not_quantities(self):
        source(self.kb, "2026-10-07-pm", "INC-2291 postmortem (Orion v4.2). Root cause: the Checkout team added a new column to the orders table. The load landed at 6:30.")
        note(self.kb, "inc", ['INC-2291 (v4.2): the Checkout team added a new column. [src: 2026-10-07-pm §1 "the Checkout team added a new column"]',
                              'The load landed at 06:30. [src: 2026-10-07-pm §1 "The load landed at 6:30"]'])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_unglued_version_numbers_must_be_in_the_cited_source(self):
        # "Policy 2.1" / "Orion 4.2" / "Abschnitt 4" are not exempt: language-free rule, safe fail
        source(self.kb, "2026-10-07-pm2", "Under Policy 2.1 the Checkout team added a new column.")
        source(self.kb, "2026-10-07-pm3", "The Checkout team added a new column.")
        note(self.kb, "inc2", ["Under Policy 2.1 the Checkout team added a new column. [src: 2026-10-07-pm3 §1]"])
        self.assertIn("2.1", self.check())
        note(self.kb, "inc2", ["Under Policy 2.1 the Checkout team added a new column. [src: 2026-10-07-pm2 §1]"])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_quote_with_brackets(self):
        source(self.kb, "2026-10-10-sched", "| [12.x][] | **Active LTS** | [Erbium][] | 2019-04-23 | 2019-10-21 | 2020-10-20 | April 2022 |")
        note(self.kb, "sched", ['Node.js 12 enters maintenance on 2020-10-20. [src: 2026-10-10-sched §t "[12.x][] | **Active LTS** | [Erbium][] | 2019-04-23 | 2019-10-21 | 2020-10-20"]'])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_decimal_comma_and_zeros(self):
        source(self.kb, "2026-10-08-de", "Die Aufbewahrung betraegt 3,5 Tage. Der Lauf dauert 1.05 h. Gebuehr EUR 1,20. Es sind 1.204 Zeilen.")
        for bad in ('Retention is 35 days. [src: 2026-10-08-de §1 "Die Aufbewahrung betraegt 3,5 Tage"]',
                    'The run takes 1.5 h. [src: 2026-10-08-de §1 "Der Lauf dauert 1.05 h"]',
                    'The fee is EUR 120. [src: 2026-10-08-de §1 "Gebuehr EUR 1,20"]'):
            note(self.kb, "de", [bad])
            self.assertIn("not in any cited source", self.check(), bad)
        note(self.kb, "de", ['Retention is 3.5 days. [src: 2026-10-08-de §1 "Die Aufbewahrung betraegt 3,5 Tage"]',
                             'There are 1,204 rows. [src: 2026-10-08-de §1 "Es sind 1.204 Zeilen"]'])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_typographic_quotes_match(self):
        source(self.kb, "2026-10-09-fr", "Le fournisseur dit « livraison en 5 jours » et „sofort verfügbar“.")
        note(self.kb, "fr", ["Delivery takes 5 days per the vendor. [src: 2026-10-09-fr §1 \"dit 'livraison en 5 jours'\"]",
                             "It is available at once. [src: 2026-10-09-fr §1 \"et 'sofort verfügbar'\"]"])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_markdown_emphasis_quote(self):
        source(self.kb, "2026-10-01-page", "| Tier | Limit |\n|---|---|\n| batch | **4,000** req/s for batch jobs |")
        note(self.kb, "page", ['Batch jobs are limited to 4,000 req/s. [src: 2026-10-01-page §t "4,000 req/s for batch jobs"]'])
        self.assertRegex(self.check(), r"(?m)^0 problem")

    def test_observed_citation_rejected(self):
        note(self.kb, "obs", ['It returned 12 rows. [src: observed 2026-01-01 work/x.md "returned 12 rows"]'])
        self.assertIn("'observed' citations are not allowed", self.check())

    def test_citation_swap_visible_in_verify(self):
        note(self.kb, "api", ['API Alpha is limited to 4,000 req/s. [src: 2026-09-30-limits §1 "batch API Alpha is limited to 4,000 req/s"]'])
        commit(self.kb)
        p = self.kb / "notes/api.md"
        p.write_text(p.read_text(encoding="utf-8").replace("batch API Alpha is limited to 4,000 req/s", "interactive API Beta allows 500 req/s"), encoding="utf-8", newline="\n")
        self.assertIn("1 new/changed", run_kb(self.kb, "verify").stdout)

    def test_verify_flags_date_and_frontmatter(self):
        note(self.kb, "delta", ['API Delta is limited to 4,000 req/min since 2031-05-05. [src: 2026-09-30-limits §1 "batch API Alpha is limited to 4,000 req/s"]'])
        out = run_kb(self.kb, "verify").stdout
        self.assertIn("DATE NOT IN SOURCE", out)
        self.assertIn("FRONTMATTER summary", out)

    def test_verify_shows_newer_uncited_source_first(self):
        # case E: a citation must not anchor the review - the newest source on the subject comes first
        source(self.kb, "2026-11-02-limits-update", "From November the batch API Alpha is limited to 6,000 req/s.", date="2026-11-02")
        note(self.kb, "alpha", ["The batch API Alpha is limited to 4,000 req/s. [src: 2026-09-30-limits §1]"])
        out = run_kb(self.kb, "verify").stdout
        self.assertIn("SOURCES ON THIS SUBJECT", out)
        self.assertLess(out.index("2026-11-02-limits-update"), out.index("2026-09-30-limits  (cited)"))

    def test_coverage_counts_unquoted_claims(self):
        note(self.kb, "alpha", ["The batch API Alpha is limited to 4,000 req/s. [src: 2026-09-30-limits §1]"])
        out = run_kb(self.kb, "coverage", "2026-09-30-limits").stdout
        self.assertNotIn("4,000", out)   # covered by an unquoted claim citing the source
        self.assertIn("500", out)        # Beta's limit is not filed yet

    def test_prose_outside_bullets_fails(self):
        note(self.kb, "prose", ['API Alpha is limited to 4,000 req/s. [src: 2026-09-30-limits §1 "batch API Alpha is limited to 4,000 req/s"]'])
        p = self.kb / "notes/prose.md"
        p.write_text(p.read_text(encoding="utf-8") + "\nAlpha also allows 9,000 req/s for VIPs.\n", encoding="utf-8", newline="\n")
        self.assertIn("text outside a claim bullet", self.check())

    def test_search_scopes(self):
        put(self.kb, "reports/answers/2026-10-01-vendors.md", "# Vendor comparison\nQuantel offers satellite links at 40 ms.\n")
        put(self.kb, "work/notes.txt", "scratch: Quantel trial key expires Friday\n")
        self.assertNotIn("reports/", run_kb(self.kb, "search", "Quantel", "--keyword").stdout)
        self.assertIn("reports/answers", run_kb(self.kb, "search", "Quantel", "--in", "reports", "--keyword").stdout)
        out = run_kb(self.kb, "search", "Quantel", "--all", "--keyword").stdout
        self.assertIn("work/notes.txt", out)
        self.assertNotIn("tools/", out)
        self.assertNotEqual(run_kb(self.kb, "search", "x", "--in", "tools").returncode, 0)

    def test_non_note_rows_are_labelled(self):
        put(self.kb, "inbox/2026-10-02-blocked-quota.md", "## q\nclaim: Orion quota is 5 TB\nblocked: reviewer\n")
        put(self.kb, "work/guess.txt", "Orion quota maybe 9 TB\n")
        out = run_kb(self.kb, "search", "Orion quota", "--all", "--keyword").stdout
        self.assertIn("BLOCKED", out)
        self.assertIn("RAW - not reviewed", out)

    def test_guard_selftest_passes(self):  # moved out of every `check` into the suite
        import importlib.util, sys
        spec = importlib.util.spec_from_file_location("kbmod", self.kb / "tools" / "kb.py")
        old = sys.argv
        sys.argv = ["kb.py"]
        import os
        cwd = os.getcwd()
        os.chdir(self.kb)
        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(mod.guard_selftest(), [])
        finally:
            os.chdir(cwd)
            sys.argv = old

    def test_verify_new_subfolder(self):
        commit(self.kb)
        note(self.kb, "api", ['API Alpha is limited to 4,000 req/s. [src: 2026-09-30-limits §1 "batch API Alpha is limited to 4,000 req/s"]'], folder="apis")
        self.assertIn("## api", run_kb(self.kb, "verify").stdout)

    def test_history_deletion_fails(self):
        note(self.kb, "ca", [f'Production changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        put(self.kb, "history/ca.md", f'## Superseded {TODAY}\n- Old claim text about approvals here. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]\nreason: changed\n')
        commit(self.kb)
        (self.kb / "history/ca.md").unlink()
        self.assertIn("history entry removed", self.check())

    def test_claim_edit_without_history_fails(self):
        note(self.kb, "ca", [f'Production changes need 2 approvals for all prod systems. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'])
        commit(self.kb)
        p = self.kb / "notes/ca.md"
        p.write_text(p.read_text(encoding="utf-8").replace("prod systems", "staging systems"), encoding="utf-8", newline="\n")
        self.assertIn("without a history/ entry", self.check())

    def test_source_edit_fails_but_past_history_does_not_poison(self):
        commit(self.kb)
        p = self.kb / "sources/files/2026-09-29-policy.md"
        p.write_text(p.read_text(encoding="utf-8") + "extra\n", encoding="utf-8", newline="\n")
        self.assertIn("source edited after it was frozen", self.check())

    def test_coverage_lists_uncovered_rule_sentences(self):
        source(self.kb, "2026-10-07-pm", "We had coffee. Schema changes must be posted 3 business days ahead. Lunch was nice today.")
        out = run_kb(self.kb, "coverage", "2026-10-07-pm").stdout
        self.assertIn("must be posted 3 business days", out)
        self.assertNotIn("coffee", out)
        put(self.kb, "inbox/x.md", '## n\nclaim: x\nevidence: [src: 2026-10-07-pm §1 "must be posted 3 business days ahead"]\n')
        self.assertNotIn("must be posted", run_kb(self.kb, "coverage", "2026-10-07-pm").stdout.split("\n")[0])

    def test_search_inflections_and_compounds(self):
        put(self.kb, "notes/bewaar.md", "---\ntitle: Bewaartermijnen klantgegevens\ntype: topic\nsummary: Hoe lang klantgegevens bewaard worden\n---\n- Klantgegevens worden 7 jaar bewaard. [src: x §1 \"x\"]\n")
        put(self.kb, "notes/umfrage.md", "---\ntitle: Kundenzufriedenheitsumfrage\ntype: topic\nsummary: Jaehrliche Umfrage\n---\n- Die Umfrage laeuft im März. [src: x §1 \"x\"]\n")
        put(self.kb, "notes/eu.md", "---\ntitle: Data residency\ntype: topic\nsummary: Where data is stored\n---\n- Customer data stays in the EU region. [src: x §1 \"x\"]\n")
        hit = lambda q: run_kb(self.kb, "search", q, "--keyword").stdout
        self.assertIn("bewaar", hit("bewaartermijn"))   # singular finds plural
        self.assertIn("umfrage", hit("umfrage"))        # part of a compound
        self.assertIn("umfrage", hit("marz"))           # diacritics
        self.assertIn("eu.md", hit("EU"))               # short term

    def test_coverage_ranks_without_word_lists(self):
        source(self.kb, "2026-10-07-de", "Wir hatten Kaffee. Schema-Aenderungen muessen 3 Werktage vorher in #src-schema gemeldet werden. Das Mittagessen war gut.")
        out = run_kb(self.kb, "coverage", "2026-10-07-de", "--top", "1").stdout
        self.assertIn("3 Werktage", out)
        self.assertNotIn("Kaffee", out)

    def test_freeze_takes_date_from_file_name(self):
        (self.kb / "work").mkdir(exist_ok=True)
        (self.kb / "work/2026-09-14-ops-sync.txt").write_text("Priya Nair owns the Orion warehouse.\n", encoding="utf-8", newline="\n")
        out = run_kb(self.kb, "freeze", "work/2026-09-14-ops-sync.txt", "--kind", "meetings").stdout
        self.assertIn("[src: 2026-09-14-ops-sync", out)
        # the document's date, not the day it was frozen (verify sorts sources by it; staleness uses it)
        self.assertIn("\ndate: 2026-09-14\n", (self.kb / "sources/meetings/2026-09-14-ops-sync.md").read_text(encoding="utf-8"))

    def test_freeze_is_byte_exact(self):
        put(self.kb, "work/meeting.txt", "Line one.\nDecision: we keep 2 approvals.\n")
        out = run_kb(self.kb, "freeze", "work/meeting.txt", "--kind", "meetings", "--title", "Weekly sync").stdout
        path = [w for w in out.split() if w.startswith("sources/")][0]
        text = (self.kb / path).read_text(encoding="utf-8")
        self.assertTrue(text.endswith("Line one.\nDecision: we keep 2 approvals.\n"))
        self.assertIn("sha256:", text)


class Freshness(unittest.TestCase):
    def setUp(self):
        self.kb = make_kb()
        source(self.kb, "2026-09-29-vendors", "Zed has been our supplier since 2020-03-01 under the master agreement.")

    def test_since_stamp_not_stale(self):
        note(self.kb, "zed", ['Zed is our supplier since 2020-03-01. [src: 2026-09-29-vendors §1 "Zed has been our supplier"]'], ntype="vendor")
        self.assertIn("0 note(s) with stale", run_kb(self.kb, "stats", "--stale", "--today", "2026-10-15").stdout)

    def test_future_stamp_does_not_keep_fresh(self):
        note(self.kb, "zed", ['Zed is our supplier (as of 2031-01-01). [src: 2026-09-29-vendors §1 "Zed has been our supplier"]'], ntype="vendor")
        self.assertIn("1 note(s) with stale", run_kb(self.kb, "stats", "--stale", "--today", "2027-06-01").stdout)

    def test_resolved_open_item_hidden(self):
        note(self.kb, "zed", ['Zed is our supplier. [src: 2026-09-29-vendors §1 "Zed has been our supplier"]'], ntype="vendor")
        put(self.kb, "meta/open-questions.md", "# open\n- RESOLVED 2026-11-01: [[zed]] contract owner unclear\n- [[zed]] renewal date unknown\n")
        out = run_kb(self.kb, "search", "Zed supplier").stdout
        self.assertIn("renewal date unknown", out)
        self.assertNotIn("contract owner unclear", out)


class SearchAndConfig(unittest.TestCase):
    def test_golden_header_ignored(self):
        kb = make_kb()
        put(kb, "eval/golden.md", (TEMPLATE / "eval/golden.md").read_text(encoding="utf-8") + "\nQ01 | who approves? | Data Platform | process | notes: x\n")
        self.assertIn("1 queries", run_kb(kb, "search-eval", "eval/golden.md").stdout)

    def test_misses_not_logged_to_tracked_files(self):
        kb = make_kb()
        run_kb(kb, "search", "secretprojectname zanzibar merger")
        self.assertFalse((kb / "meta/search-misses.log").exists())

    def test_forget_check_finds_leftovers(self):
        kb = make_kb()
        put(kb, "inbox/processed/2026-11-13-x.md", "claim: Project Zanzibar merger is planned\n")
        out = run_kb(kb, "forget-check", "Zanzibar merger").stdout
        self.assertIn("inbox/processed/2026-11-13-x.md", out)

    def test_kb_toml_types(self):
        kb = make_kb()
        p = kb / "kb.toml"
        p.write_text(p.read_text(encoding="utf-8").replace('"dataset"', '"dataset", "case"'), encoding="utf-8", newline="\n")
        source(kb, "2026-09-29-policy", POLICY)
        note(kb, "c1", [f'Production changes need 2 approvals. [src: 2026-09-29-policy §1 "{POLICY[:40]}"]'], ntype="case")
        self.assertRegex(run_kb(kb, "check").stdout, r"(?m)^0 problem")

    def test_env_file_ignored_for_embeddings(self):
        kb = make_kb()
        put(kb, ".env", "KB_EMBED_URL=http://attacker.example/v1\nKB_EMBED_MODEL=x\n")
        sys.path.insert(0, str(kb / "tools"))
        import importlib
        import kbsem
        importlib.reload(kbsem)
        self.assertIsNone(kbsem.config(kb))


class Fetch(unittest.TestCase):
    def test_rejects_long_query_and_local(self):
        kb = make_kb()
        import subprocess
        from helpers import clean_env
        # URL validation happens before trafilatura is imported, so plain python can test it
        run = lambda url: subprocess.run([sys.executable, "tools/fetch.py", url, "--slug", "x"], cwd=kb,
                                         capture_output=True, text=True, env=clean_env())
        r = run("https://example.com/?d=" + "a" * 200)
        self.assertIn("query", r.stdout + r.stderr)
        r = run("http://127.0.0.1/x")
        self.assertIn("non-public", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
