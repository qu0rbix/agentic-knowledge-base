"""Set up a case-B run KB: template copy, initialised charter, frozen sources (kb.py freeze), owner message,
inbox batches built from candidates.json (mutation labels and hints stripped). Usage: setup_run.py <run_dir> <template>"""
import json, shutil, subprocess, sys
from pathlib import Path

B = Path(__file__).parent
run, template = Path(sys.argv[1]), Path(sys.argv[2])
if run.exists():
    import os, stat
    shutil.rmtree(run, onexc=lambda f, x, e: (os.chmod(x, stat.S_IWRITE), f(x)))
shutil.copytree(template, run, ignore=shutil.ignore_patterns("__pycache__", ".cache", ".kb-guard"))
g = lambda *a: subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a], cwd=run, capture_output=True, text=True)
g("init", "-q")

(run / "charter.md").write_text("""# Charter - Data Platform team knowledge base

## Purpose
Help the data platform lead (the owner) answer questions about our systems, vendors, SLAs, costs, data-retention
rules, owners and decisions, and keep that knowledge correct as it changes.

## In scope
Systems we run (Orion, Cobalt, ...), vendors and contracts (prices, renewal terms, security reviews), SLAs and
incidents' durable lessons, data retention and deletion policy, budget caps, owners and decision rights, decisions.
## Out of scope
To-dos and task status, chit-chat, one-off workarounds, marketing claims, personal opinions, anything about other teams' internals.

## Admission test (all must hold)
1. In scope. 2. Durable (still true next month unless reality changes). 3. Consequential (someone would act on it).
4. Not derivable in a minute from a source we already hold. 5. Supported by a quote from a frozen source or the owner's own words.
6. Stated precisely: entity, number, unit, scope, conditions, dates. 7. Not marketing or speculation; "considering" is not "decided".

## Trust tiers
1 the owner, official internal policy; 2 colleagues, internal threads, a vendor about its own product terms;
3 reputable third parties; 4 marketing pages, unknown. A tier-4 source is never the only support for a number or capability claim.

## Conflict rule
Never average or pick silently. Newer + more authoritative supersedes (old value to history/); otherwise log the
conflict in meta/open-questions.md with both sources and file neither as current.

## Approval
Small splits and aliases: no approval. Structure moves, deletions, charter changes: the owner.
""", encoding="utf-8", newline="\n")

kind_of = lambda n: "meetings" if "sync" in n or "notes" in n or "postmortem" in n else "chat" if "slack" in n else \
    "email" if "thread" in n else "files"
tier_of = lambda n: "4" if "pricing" in n else "1" if "policy" in n else "2"
for src in sorted((B / "sources").glob("*.txt")):
    stem = src.stem
    date, slug = stem[:10], stem[11:]
    (run / "work").mkdir(exist_ok=True)
    shutil.copy(src, run / "work" / src.name)
    r = subprocess.run([sys.executable, "tools/kb.py", "freeze", f"work/{src.name}", "--kind", kind_of(stem),
                        "--date", date, "--slug", slug, "--tier", tier_of(stem), "--title", slug.replace("-", " ")],
                       cwd=run, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr + r.stdout
# a real owner message on 2026-10-16 (as the capture hook would have saved it), unrelated to the budget increase
(run / "sources" / "user").mkdir(parents=True, exist_ok=True)
(run / "sources" / "user" / "2026-10-16-093000-1.md").write_text(
    "---\nid: 2026-10-16-093000-1\ntype: user\ntitle: owner message\ndate: 2026-10-16\ntier: 1\n---\n"
    "Keep the FY27 numbers in the KB as the finance thread states them; I have not agreed to any increase.\n",
    encoding="utf-8", newline="\n")
shutil.rmtree(run / "work")
(run / "work").mkdir()
(run / "work" / ".gitkeep").write_text("")
g("add", "-A")
g("commit", "-qm", "case B start")

cands = json.loads((B / "candidates.json").read_text(encoding="utf-8"))
import re
sid = lambda f: Path(f).stem[:11] + re.sub(r"[^a-z0-9-]+", "-", Path(f).stem[11:].lower()).strip("-")[:50]
batches = [cands[i:i + 16] for i in range(0, len(cands), 16)]
for n, batch in enumerate(batches, 1):
    out = []
    for c in batch:
        if c["kind"] == "invented_owner_quote":
            ev = f'[src: user 2026-10-16 "{c["evidence_quote"]}"]'
        else:
            ev = f'[src: {sid(c["evidence_source"])} §1 "{c["evidence_quote"]}"]'
        out.append(f"## {c['cid']} {c['question'][:60]}\nclaim: {c['claim']}\nquestion: {c['question']}\n"
                   f"why: from {sid(c['evidence_source'])}\nevidence: {ev}\ntarget: {c['target']}\n")
    (B / f"batch{n}.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
print(f"run ready at {run}; {len(batches)} batches in {B}")
