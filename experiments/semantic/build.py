"""Build a benchmark KB from bench.json (+ optional extra.json) into argv[1] (a copy of template/); write queries.txt."""
import json, sys
from pathlib import Path

R = Path(sys.argv[1])
B = Path(__file__).parent
d = json.loads((B / "bench.json").read_text(encoding="utf-8"))
extra = json.loads((B / "extra.json").read_text(encoding="utf-8")) if (B / "extra.json").exists() else {}
titles = {}
for n in d["notes"]:
    folder = R / "notes" / (n.get("folder") or "")
    folder.mkdir(parents=True, exist_ok=True)
    titles[n["id"]] = n["title"]
    al = ", ".join(a.replace(",", " ") for a in n.get("aliases", []))
    claims = "\n".join(f"- {c} [src: bench-source §1]" for c in n["claims"])
    (folder / f"{n['id']}.md").write_text(
        f"---\nid: {n['id']}\ntype: {n.get('type', 'topic')}\ntitle: {n['title']}\nsummary: {n['summary']}\n"
        f"aliases: [{al}]\nstatus: current\nupdated: 2026-10-01\n---\n## Claims\n{claims}\n", encoding="utf-8")
hist = {}
for h in d.get("history", []):
    hist.setdefault(h["note"], []).append(h["claim"])
(R / "history").mkdir(exist_ok=True)
for nid, cs in hist.items():
    (R / "history" / f"{nid}.md").write_text(
        f"# History: {nid}\n## Superseded 2026-06-01\n" + "\n".join(f"- {c} [src: bench-source §1]" for c in cs)
        + "\nreason: changed - benchmark\n", encoding="utf-8")
lines = [f"{q['q']} | {','.join(q['expected'])} | {q['kind']}" for q in d["queries"] + extra.get("queries", [])]
(B / "queries.txt").write_text("\n".join(l.replace("\n", " ") for l in lines) + "\n", encoding="utf-8")
print(len(d["notes"]), "notes;", len(lines), "queries")
