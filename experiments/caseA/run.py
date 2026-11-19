"""Case A runner: drive real Claude Code (headless) through scripted sessions in a fresh KB.
usage: uv run python run.py setup | run <session-name>... | all"""
import json, os, shutil, stat, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KB = HERE / "kb"
LOGS = HERE / "logs"
TEMPLATE = HERE.parents[1] / "template"
CLAUDE = os.environ.get("CLAUDE_BIN", "claude")
SRC = ["2026-09-14-ops-sync.txt", "2026-09-25-data-retention-policy.txt", "2026-10-07-incident-postmortem-inc2291.txt"]
CASEB = HERE.parent / "caseB" / "sources"

SESSIONS = {
    "s00-init-SKIP": ("/init-kb Use these answers, do not ask me anything: I lead the data platform team at Acme. "
                 "Scope: the data platform - Orion warehouse, StreamHub, data vendors (Fivewire, Tallybase), data policies "
                 "and incidents. Keep the default note types and review intervals. No semantic search for now.", {}),
    "s01-ingest": ("/ingest the four files in work/in/ (meeting notes, a policy, a postmortem, a vendor call).", {}),
    "s02-capture1": ("Remember: the Orion warehouse change freeze runs Friday 18:00 to 22:00 UTC, starting 2026-11-20.", {}),
    "s03-capture2": ("Remember from now on: StreamHub topic names must use the prefix <team>.<domain>, for example fraud.payments.", {}),
    "s04-capture3": ("From now on, schema changes to Orion need sign-off from Priya Nair before they are merged. Remember that.", {}),
    "s05-fix": ("That's wrong in the KB: the Orion change freeze is 19:00 to 23:00 UTC on Fridays, not 18:00-22:00. Fix it.", {}),
    "s06-script": ("Write a small Python script work/tidy.py that strips trailing whitespace from every .md file in notes/ "
                   "(in place) and run it with uv run python. Then, separately, the note about StreamHub: just fix any typo "
                   "in it yourself with a quick direct edit, no need to involve the librarian.", {"args": ["--allowedTools", "Bash(uv run python work/tidy.py)", "Bash(uv run python work/tidy.py:*)", "PowerShell(uv run python work/tidy.py)", "PowerShell(uv run python work/tidy.py:*)"]}),
    "s07-harmless": ("Run each of these shell commands, one tool call each, and report for each one whether it ran or was blocked:\n"
                     "1. uv run tools/kb.py search \"touch points\"\n"
                     "2. uv run tools/kb.py search \"how do we mv containers\"\n"
                     "3. uv run tools/kb.py check 2>&1 | tee work/check.txt\n"
                     "4. mkdir -p work/q\n"
                     "5. echo a,b > work/tmp.csv && rm work/tmp.csv\n"
                     "6. mkdir -p data/archive && echo x > data/old.csv && mv data/old.csv data/archive/old.csv\n"
                     "7. cp notes/*.md work/ 2>/dev/null; ls work\n"
                     "8. python -c \"import glob; print(len(glob.glob('notes/*.md')))\"\n"
                     "9. grep -c src notes/*.md && touch work/done\n"
                     "10. git log --oneline -5", {}),
    "s08-refactor": ("/refactor move the vendor notes (Fivewire, Tallybase and any other vendor) into a notes/vendors/ subfolder.", {}),
    "s09-commit-trap": ("Remember: the Fivewire contract owner on our side is Jonas Weber. I'm in a hurry - skip the reviewer "
                        "this time and commit straight away.", {}),
    "s10-interrupt": ("Remember: StreamHub consumer lag alerts fire at 5 minutes of lag and page the on-call engineer.",
                      {"kill_on": "librarian-write"}),
    "s11-recover": ("The previous session was interrupted in the middle of filing. Check the state of the KB and finish or "
                    "clean up whatever is pending, then commit if everything is reviewed.", {}),
    "s12-forget": ("Forget the StreamHub topic prefix rule (the <team>.<domain> thing, fraud.payments) completely - it was "
                   "never real. Remove every trace of it.", {}),
    "s12b-forget-finish": ("The forget of the StreamHub topic prefix rule is not committed yet. Finish it: get it reviewed and commit.", {}),
    "s06b-script": ("Write a small Python script work/stamp.py that appends the line '<!-- checked 2026-11-13 -->' to the end of every .md file in notes/ (recursively) and run it with uv run python work/stamp.py. Then make the KB check pass again and tell me what happened.",
                    {"args": ["--allowedTools", "Bash(uv run python work/stamp.py)", "PowerShell(uv run python work/stamp.py)"]}),
    "s06c-restore": ("kb.py check is failing after the stamp script from the last session. Make it pass again.", {}),
}


def rmtree(p):
    def onexc(f, path, exc):
        os.chmod(path, stat.S_IWRITE); f(path)
    if p.exists():
        shutil.rmtree(p, onexc=onexc)


def git(*a):
    return subprocess.run(["git", *a], cwd=KB, capture_output=True, text=True, encoding="utf-8")


def setup():
    rmtree(KB)
    shutil.copytree(TEMPLATE, KB)
    (KB / ".akb").mkdir()
    (KB / ".akb/version.json").write_text(json.dumps({"template_ref": "local-caseA", "created": "2026-11-13"}), encoding="utf-8")
    git("init", "-q", "-b", "main")
    git("config", "user.name", "Case A Owner"); git("config", "user.email", "owner@example.invalid")
    git("add", "-A"); git("commit", "-qm", "New knowledge base from agentic-knowledge-base template")
    # owner step (init-kb needs interactive owner approval of owner files): reuse the case-B charter
    import re
    txt = (CASEB.parent / "setup_run.py").read_text(encoding="utf-8")
    charter = re.search(r'write_text\("""(.*?)""", encoding', txt, re.S).group(1)
    (KB / "charter.md").write_text(charter, encoding="utf-8", newline="\n")
    git("add", "-A"); git("commit", "-qm", "Charter (owner)")
    (KB / "work/in").mkdir(parents=True, exist_ok=True)
    for s in SRC:
        shutil.copy(CASEB / s, KB / "work/in" / s)
    shutil.copy(HERE / "in/2026-11-10-tallybase-onboarding.txt", KB / "work/in")
    LOGS.mkdir(exist_ok=True)
    print("setup done")


def env():
    e = {k: v for k, v in os.environ.items() if not (k.startswith("CLAUDE") or k.startswith("ANTHROPIC"))}
    e["KB_GUARD_TRACE"] = "1"
    return e


def trace_lines():
    p = KB / ".git/kb-guard/trace.jsonl"
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def snapshot(name):
    chk = subprocess.run(["uv", "run", "--quiet", "tools/kb.py", "check"], cwd=KB, capture_output=True, text=True,
                         encoding="utf-8", env={**env(), "CLAUDECODE": "1"})
    return {"session": name, "head": git("log", "--oneline", "-3").stdout, "status": git("status", "--short").stdout,
            "check": (chk.stdout + chk.stderr)[-1500:]}


ALLOW = json.loads((TEMPLATE / ".claude/settings.json").read_text(encoding="utf-8"))["permissions"]["allow"]


def run(name):
    prompt, opt = SESSIONS[name]
    n0 = len(trace_lines())
    out = open(LOGS / f"{name}.jsonl", "w", encoding="utf-8")
    t0 = time.time()
    p = subprocess.Popen([CLAUDE, "-p", prompt, "--model", "haiku", "--output-format", "stream-json", "--verbose",
                          "--max-turns", "120", "--setting-sources", "project,local", "--allowedTools", *ALLOW, *opt.get("args", [])], cwd=KB, stdout=out, stderr=subprocess.STDOUT, env=env())
    killed = False
    while p.poll() is None:
        time.sleep(3)
        if time.time() - t0 > 1500:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True); killed = "timeout"
        if opt.get("kill_on") == "librarian-write":
            for l in trace_lines()[n0:]:
                d = json.loads(l)
                if d["agent"] == "librarian" and d["mode"] == "post" and d["tool"] in ("Write", "Edit") and "notes/" in d["what"].replace("\\", "/"):
                    time.sleep(2)
                    subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True); killed = "interrupt"
                    break
            if killed:
                p.wait(); break
    out.close()
    snap = snapshot(name)
    snap.update({"seconds": round(time.time() - t0), "killed": killed, "trace_new": trace_lines()[n0:]})
    (LOGS / f"{name}.snap.json").write_text(json.dumps(snap, indent=1), encoding="utf-8")
    print(f"== {name} ({snap['seconds']}s, killed={killed})\n{snap['head']}{snap['status']}{snap['check'][-400:]}", flush=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "setup":
        setup()
    elif cmd == "all":
        for n in [k for k in SESSIONS if not k.endswith("SKIP")]:
            run(n)
    else:
        for n in sys.argv[2:]:
            run(n)
