"""Case D scoring: automated metrics per run + an anonymised package per run for the blind judge.
usage: uv run python score.py <run-dir-name>... (e.g. lean1 full1 plain1)"""
import json, random, re, shutil, subprocess, sys
from pathlib import Path

H = Path(__file__).parent


def git(kb, *a):
    return subprocess.run(["git", *a], cwd=kb, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def session_stats(logs):
    out = {}
    for f in sorted(logs.glob("s*.jsonl")):
        res, denied, tools, text = {}, 0, 0, ""
        for l in f.open(encoding="utf-8", errors="replace"):
            try:
                d = json.loads(l)
            except ValueError:
                continue
            if d.get("type") == "assistant":
                for c in d["message"]["content"]:
                    if c["type"] == "tool_use":
                        tools += 1
                    elif c["type"] == "text" and not d.get("parent_tool_use_id") and len(c["text"]) > 300 and c["text"].strip() not in text:
                        text = (text + "\n\n" + c["text"].strip()).strip()  # the answer may precede a hook-driven extra turn
            if d.get("type") == "result":
                res = d
                denied = len(d.get("permission_denials") or [])
                t = (d.get("result") or "").strip()
                if t and t not in text:
                    text = (text + "\n\n" + t).strip()  # a session can end several times (background agents report back)
        out[f.stem] = {"cost": round(res.get("total_cost_usd") or 0, 4), "turns": res.get("num_turns"), "tools": tools,
                       "denied": denied, "seconds": round((res.get("duration_ms") or 0) / 1000), "final": text}
    return out


def unreviewed_commits(kb):
    """Commits that change notes/ or history/ without adding an approved review file (pure renames excluded)."""
    bad = []
    for sha in git(kb, "rev-list", "--reverse", "HEAD").split()[1:]:
        files = git(kb, "show", "--name-status", "--format=", sha).splitlines()
        kbfiles = [l for l in files if re.search(r"\t(notes|history)/", l) and not l.startswith("R100")]
        if not kbfiles:
            continue
        reviews = [l.split("\t")[-1] for l in files if "meta/audits/" in l and l[0] in "AM"]
        ok = any(re.search(r"(?mi)^\**verdict:?\**\s*approved", git(kb, "show", f"{sha}:{r}")) for r in reviews)
        if not ok:
            bad.append(git(kb, "log", "--format=%h %s", "-1", sha).strip())
    return bad


def forget_residue(kb):
    words = ["Crunchy", "CDX-4471"]
    tree = [p.relative_to(kb).as_posix() for p in kb.rglob("*") if p.is_file() and ".git" not in p.parts
            and any(w.lower() in p.read_text(encoding="utf-8", errors="ignore").lower() for w in words)]
    hist = git(kb, "log", "--all", "-p", "--format=%h")
    return {"working_tree": tree, "in_git_history": any(w.lower() in hist.lower() for w in words)}


def main(names):
    jroot = H / "judge"
    jroot.mkdir(exist_ok=True)
    labels = {}
    letters = list("ABCDEFGH")
    random.Random(7).shuffle(letters)
    report = {}
    for i, name in enumerate(names):
        run = H / "runs" / name
        kb = run / "kb"
        st = session_stats(run / "logs")
        chk = subprocess.run(["uv", "run", "--quiet", "tools/kb.py", "check"], cwd=kb, capture_output=True, text=True,
                             encoding="utf-8") if (kb / "tools/kb.py").exists() else None
        report[name] = {
            "cost_total": round(sum(s["cost"] for s in st.values()), 2),
            "seconds_total": sum(s["seconds"] for s in st.values()),
            "tool_calls": sum(s["tools"] for s in st.values()),
            "denied_total": sum(s["denied"] for s in st.values()),
            "denied_median_per_session": sorted(s["denied"] for s in st.values())[len(st) // 2] if st else None,
            "commits": len(git(kb, "rev-list", "HEAD").split()) - 1,
            "unreviewed_commits": unreviewed_commits(kb) if name[:4] != "plai" else "n/a",
            "forget": forget_residue(kb),
            "check_last": (chk.stdout.strip().splitlines() or [""])[-1] if chk else "n/a",
            "notes": len(list((kb / "notes").rglob("*.md"))),
            "history_files": len(list((kb / "history").rglob("*.md"))) if (kb / "history").exists() else 0,
            "per_session": {k: {x: v[x] for x in ("cost", "tools", "denied", "seconds")} for k, v in st.items()},
        }
        # anonymised judge package: notes, history, open questions, answers - no scaffold files, no arm name
        lab = letters[i]
        labels[lab] = name
        d = jroot / f"kb_{lab}"
        if d.exists():
            shutil.rmtree(d)
        for sub in ("notes", "history", "archive"):
            if (kb / sub).exists():
                shutil.copytree(kb / sub, d / sub, ignore=shutil.ignore_patterns(".gitkeep"))
        for f in ("meta/open-questions.md", "meta/parking.md"):
            if (kb / f).exists():
                (d / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(kb / f, d / f)
        ans = "\n\n".join(f"## {k}\n{st[k]['final']}" for k in ("s15", "s20", "s21", "s22") if k in st)
        (d / "ANSWERS.md").write_text(ans, encoding="utf-8")
    (jroot / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
    (H / "auto_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    for n, r in report.items():
        print(n, {k: v for k, v in r.items() if k != "per_session"})


if __name__ == "__main__":
    main(sys.argv[1:])
