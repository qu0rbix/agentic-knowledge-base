"""Build anonymised judge packages + automatic metrics. usage: uv run python pack.py <run>..."""
import json, random, shutil, string, sys
from pathlib import Path

H = Path(__file__).parent
sys.path.insert(0, str(H.parent / "caseD"))
import score  # case D scorer: session_stats, forget_residue

runs = sys.argv[1:]
labels = list(string.ascii_uppercase[:len(runs)])
random.Random(11).shuffle(labels)
J = H / "judge"
J.mkdir(exist_ok=True)
lab_map, auto = {}, {}
for run, lab in zip(runs, labels):
    kb = H / "runs" / run / "kb"
    d = J / f"kb_{lab}"
    if d.exists():
        shutil.rmtree(d)
    for sub in ("notes", "history"):
        if (kb / sub).exists():
            shutil.copytree(kb / sub, d / sub, ignore=shutil.ignore_patterns(".gitkeep"))
    st = score.session_stats(kb.parent / "logs")
    (d / "ANSWERS.md").write_text("\n\n".join(f"## {k}\n{st[k]['final']}" for k in ("s21", "s22") if k in st), encoding="utf-8")
    r = H / "reader" / run / "answers.md"
    if r.exists():
        shutil.copy(r, d / "READER.md")
    a = H / "audit" / run
    if (a / "plants.json").exists():
        shutil.copy(a / "plants.json", d / "plants.json")
        shutil.copytree(a / "kb" / "notes", d / "planted_notes")
    for f in a.glob("audit_*.md"):
        shutil.copy(f, d / f"AUDIT_{f.stem.split('_')[1]}.md")
    lab_map[lab] = run
    auto[run] = {"cost": round(sum(s["cost"] for s in st.values()), 2), "minutes": round(sum(s["seconds"] for s in st.values()) / 60),
                 "forget": score.forget_residue(kb),
                 "audits": {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in a.glob("audit_*.json")},
                 "reader": json.loads((H / "reader" / run / "stats.json").read_text(encoding="utf-8")) if (H / "reader" / run / "stats.json").exists() else None}
(J / "labels.json").write_text(json.dumps(lab_map, indent=1), encoding="utf-8")
(H / "auto.json").write_text(json.dumps(auto, indent=1), encoding="utf-8")
for k, v in auto.items():
    print(k, v["cost"], v["minutes"], v["forget"], {x: (y["cost"], y["seconds"], y["tools"]) for x, y in v["audits"].items()})
