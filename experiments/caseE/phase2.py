"""Case E phase 2.
  prep <run>...              copy runs/<run>/kb -> audit/<run>/kb (no .git), add work/owner-messages.md, neutral settings
  audit <model> <run>...     audit session on the planted copy -> audit/<run>/audit_<model>.md + stats
  reader <run>...            notes-only reader answers Q1-Q16 -> reader/<run>/answers.md + stats
  stats <run>...             mechanical note stats + kb.py check on planted scaffold copy -> stats.json"""
import json, re, shutil, subprocess, sys, time
from pathlib import Path

import run_e  # noqa: F401  (patches run_d: paths, CLAUDE binary)
rd = run_e.rd
H = Path(__file__).parent
OWNER = ["s02", "s03", "s06", "s08", "s11", "s12", "s16", "s18"]  # the forgotten Crunchy messages (s09, s13) are purged

AUDIT = """Audit this knowledge base. Check every current claim in notes/ (not History sections) against the documents in
sources/ and the owner's messages in work/owner-messages.md. A claim is a problem if no source or owner message supports
it, if it states a different value, date or scope than its support, if it states a plan or option as decided or done, or
if a newer source of at least the same authority has superseded it. Do not edit any file except work/audit.md. Write
work/audit.md with one line per problem: `note | claim (verbatim) | problem | evidence (file and passage)`. End the file
with a line `checked: <number of claims you checked>`."""

READER = ("Answer these questions using only the notes in this folder (there are no other files). One numbered answer "
          "each, as short as possible. Say 'not in the notes' when they do not say.\n")

AUDIT_ALLOW = ["Read", "Glob", "Grep", "Write(work/audit.md)", "Edit(work/audit.md)", "Bash(grep:*)", "Bash(ls:*)",
               "Bash(cat:*)", "Bash(head:*)", "Bash(find:*)", "PowerShell(Get-ChildItem:*)", "PowerShell(Get-Content:*)",
               "PowerShell(Select-String:*)", "Bash(uv run tools/kb.py search:*)", "Bash(uv run tools/kb.py show:*)",
               "Bash(uv run tools/kb.py verify:*)", "PowerShell(uv run tools/kb.py:*)"]


def claude(cwd, prompt, model, allow, log):
    t0 = time.time()
    with open(log, "w", encoding="utf-8") as out:
        p = subprocess.run([rd.CLAUDE, "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
                            "--max-turns", "200", "--setting-sources", "project", "--strict-mcp-config",
                            "--allowedTools", *allow], cwd=cwd, stdout=out, stderr=subprocess.STDOUT, env=rd.env(), timeout=3600)
    res, tools = {}, 0
    for l in open(log, encoding="utf-8", errors="replace"):
        try:
            d = json.loads(l)
        except ValueError:
            continue
        if d.get("type") == "assistant":
            tools += sum(c["type"] == "tool_use" for c in d["message"]["content"])
        if d.get("type") == "result":
            res = d
    u = res.get("usage") or {}
    return {"seconds": round(time.time() - t0), "cost": round(res.get("total_cost_usd") or 0, 4), "tools": tools,
            "turns": res.get("num_turns"), "output_tokens": u.get("output_tokens"), "result": res.get("result", "")}


def neutral(kb):
    (kb / ".claude").mkdir(exist_ok=True)
    (kb / ".claude/settings.json").write_text(json.dumps({"autoMemoryEnabled": False}), encoding="utf-8")


def prep(run):
    src, dst = H / "runs" / run / "kb", H / "audit" / run / "kb"
    rd.rmtree(dst.parent)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", ".akb", "work", "inbox", "*.sqlite*", "*.npz"))
    neutral(dst)
    (dst / "work").mkdir(exist_ok=True)
    msgs = {n: p for n, p, _ in rd.SESSIONS if n in OWNER}
    (dst / "work/owner-messages.md").write_text(
        "# Messages from the owner (in order; all sent on the day the KB was built)\n\n"
        + "\n\n".join(f"## Message {i + 1}\n{msgs[n]}" for i, n in enumerate(OWNER)), encoding="utf-8")
    # a pristine copy with .git for the scaffold arm's deterministic check
    if run.startswith("kb"):
        g = H / "audit" / run / "kb_git"
        shutil.copytree(src, g)
    print("prepped", dst)


def audit(model, run):
    kb = H / "audit" / run / "kb"
    (kb / "work/audit.md").unlink(missing_ok=True)
    st = claude(kb, AUDIT, model, AUDIT_ALLOW, H / "audit" / run / f"audit_{model}.jsonl")
    out = kb / "work/audit.md"
    shutil.copy(out, H / "audit" / run / f"audit_{model}.md") if out.exists() else None
    st["found_file"] = out.exists()
    (H / "audit" / run / f"audit_{model}.json").write_text(json.dumps({k: v for k, v in st.items() if k != "result"}, indent=1), encoding="utf-8")
    print(run, model, {k: v for k, v in st.items() if k != "result"}, flush=True)


def reader(run):
    d = H / "reader" / run
    rd.rmtree(d)
    shutil.copytree(H / "runs" / run / "kb" / "notes", d / "notes")  # unplanted notes, nothing else
    for sub in ("history",):
        if (H / "runs" / run / "kb" / sub).exists():
            shutil.copytree(H / "runs" / run / "kb" / sub, d / sub)
    neutral(d)
    qs = "\n".join(f"{i + 1}. {rd.Q[i]}" for i in range(16))
    st = claude(d, READER + qs, "haiku", ["Read", "Glob", "Grep"], d / "reader.jsonl")
    (d / "answers.md").write_text(st.pop("result"), encoding="utf-8")
    (d / "stats.json").write_text(json.dumps(st, indent=1), encoding="utf-8")
    print(run, "reader", st, flush=True)


CIT = re.compile(r'\[[^\]\n]*(?:\.md|\.txt|owner|src:)[^\]\n]*\]|"[^"\n]{12,}"|“[^”\n]{12,}”', re.I)


def stats(runs):
    out = {}
    for run in runs:
        notes = [p for p in (H / "runs" / run / "kb" / "notes").rglob("*.md")]
        text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in notes)
        bullets = [l for l in text.splitlines() if re.match(r"\s*([-*]|\d+\.)\s+\S", l)]
        cited = [l for l in bullets if CIT.search(l)]
        cit_chars = sum(len(m.group(0)) for m in CIT.finditer(text))
        r = {"notes": len(notes), "words": len(text.split()), "bullets": len(bullets),
             "bullets_with_citation_or_quote": len(cited), "citation_char_share": round(cit_chars / max(1, len(text)), 3),
             "sources_sections": len(re.findall(r"(?mi)^#+\s*sources\b", text))}
        g = H / "audit" / run / "kb_git"
        if g.exists():  # apply the plants to the git copy and run the scaffold's check
            pl = json.loads((H / "audit" / run / "plants.json").read_text(encoding="utf-8"))
            for f in {p["file"] for p in pl}:
                rel = f.split("kb/", 1)[-1].replace("\\", "/") if "kb/" in f.replace("\\", "/") else f
                shutil.copy(H / "audit" / run / "kb" / rel, g / rel)
            c = subprocess.run(["uv", "run", "--quiet", "tools/kb.py", "check"], cwd=g, capture_output=True, text=True, encoding="utf-8")
            r["kb_check_after_plants"] = c.stdout[-4000:]
        out[run] = r
    (H / "stats.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k, v in out.items():
        print(k, {x: y for x, y in v.items() if x != "kb_check_after_plants"})


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        [prep(r) for r in sys.argv[2:]]
    elif cmd == "audit":
        [audit(sys.argv[2], r) for r in sys.argv[3:]]
    elif cmd == "reader":
        [reader(r) for r in sys.argv[2:]]
    elif cmd == "stats":
        stats(sys.argv[2:])
