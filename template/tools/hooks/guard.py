#!/usr/bin/env python3
"""guard - who may write where in the KB. Stdlib only. Wired in .claude/settings.json.

Modes (first argument):
  pre       PreToolUse on Write|Edit|NotebookEdit|Bash|PowerShell. Exit 2 blocks (stderr goes to the agent).
            Touches a heartbeat that `kb.py check` verifies, so a session without working hooks fails visibly.
  post      PostToolUse / PostToolUseFailure on the same tools, for every role. Changes to protected files that the
            calling role may make are accepted into the manifest; any other change is recorded as a violation
            (.git/kb-guard/violations.json) and reported. `kb.py check` fails while a file still holds the bad content.
  manifest  SessionStart: accept the current protected files (changes made between sessions are the owner's).
  clear     Owner only, in your own terminal: accept the current state and drop recorded violations.

Roles come from the hook input `agent_type` (= the subagent's `name`; absent on the main thread -> "main").
Protected (everything else - notes/, history/, tools/, work/, data/, ... - is open; `kb.py check` guards the notes):
  existing files in sources/                                    -> nobody edits them (freeze a new source instead)
  sources/user/                                                 -> nobody (the capture hook writes the owner's words)
  charter.md CLAUDE.md CONVENTIONS.md kb.toml .env .claude/     -> the main agent through Write/Edit only (the owner approves)
  tools/hooks/ tools/kb.py tools/kbsem.py tools/fetch.py        -> same (the guard and the checks themselves)
The shell pre-check only looks at redirect targets, guard state and `git commit` (agents commit with `kb.py commit`);
everything a script does is caught by the post check instead.
Internal errors exit 2. Pair with `"onFailure": "block"` in settings so a hook that cannot start also blocks.
"""
import hashlib, json, os, re, subprocess, sys, time
from pathlib import Path, PurePosixPath

FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
KB_ZONE = ("notes/", "history/", "archive/", "decisions/", "meta/purges.tsv")
OWNER_FILES = ("charter.md", "claude.md", "conventions.md", "kb.toml", ".env")
SCAFFOLD = (".claude/", "tools/hooks/", "tools/kb.py", "tools/kbsem.py", "tools/fetch.py")  # the guard and its gate
GIT_COMMIT = re.compile(r"\bgit(?:\.exe)?['\"]?(?:\s+(?:-[cC]\s+\S+|--?[\w-]+(?:=\S+)?))*\s+commit\b", re.I)
REDIRECT = r"(?:\d?>>?|\|\s*tee(?:\s+-a)?|Out-File(?:\s+-FilePath)?|Set-Content(?:\s+-Path)?|Add-Content(?:\s+-Path)?)\s*['\"]?([^\s'\";|&)]+)"
TRACKED_DIRS = ("notes", "history", "archive", "decisions", "tools", "meta/audits", "sources", ".claude")
TRACKED_FILES = ("meta/purges.tsv", "charter.md", "CLAUDE.md", "CONVENTIONS.md", "kb.toml", ".env")


def root(data=None) -> Path:
    d = os.environ.get("CLAUDE_PROJECT_DIR") or (data or {}).get("cwd") or "."
    return Path(d).resolve()


def rel(path: str, base: Path, cwd: Path) -> str:
    p = Path(path)
    if not p.is_absolute():
        p = cwd / p
    try:
        r = p.resolve().relative_to(base)
    except ValueError:
        return "../" + p.name  # outside the KB: not our business
    return PurePosixPath(*r.parts).as_posix()


def zone(r: str) -> str:
    r = r.lower()
    if r.startswith("../"):
        return "outside"
    if r.startswith(KB_ZONE):
        return "kb"
    if r.startswith(SCAFFOLD) or r in OWNER_FILES:
        return "owner"
    if r.startswith("tools/") and not r.startswith("tools/attic/"):
        return "tools"
    if r.startswith("meta/audits/"):
        return "audits"
    if r.startswith("sources/user/"):
        return "user"
    if r.startswith("sources/"):
        return "sources"
    if r.startswith((".git/kb-guard", ".kb-guard")):
        return "guard"
    return "open"


def may_write(role: str, r: str, tool: str = "Bash") -> bool:
    z = zone(r)
    if z in ("user", "guard"):
        return False
    if z == "owner":
        return role == "main" and tool in FILE_TOOLS
    return True  # notes, history, tools, audits, new sources, work/...: open (existing sources are refused separately)


WHY = {"user": "sources/user/ holds the owner's own words and is written only by the capture hook",
       "owner": "owner and scaffold files (charter, CLAUDE.md, CONVENTIONS.md, kb.toml, .claude/, tools/hooks/, kb.py, kbsem.py, fetch.py) change only through the Edit/Write tools, with the owner's approval",
       "guard": "the guard's state is owner-only"}


def decide_file(role: str, r: str, exists: bool, tool: str):
    if zone(r) == "outside":
        return None
    if r.lower().startswith("sources/") and exists:
        return "sources/ is immutable evidence: freeze a new source instead of editing one"
    if not may_write(role, r, tool):
        return WHY[zone(r)]
    return None


def load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def state_dir(base: Path, create: bool = False) -> Path:
    # inside .git so it is never committed; a KB without git gets a git-ignored .kb-guard/
    d = (base / ".git" / "kb-guard") if (base / ".git").is_dir() else (base / ".kb-guard")
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def restoring_violations(base: Path, cmd: str) -> bool:
    """Allow restoring/deleting exactly the files the guard recorded as violations."""
    viol = load(state_dir(base) / "violations.json", {})
    if re.search(r"[;&|`]|\$\(", cmd):  # only a single, plain command may use this exemption
        return False
    if not viol or not re.match(r"\s*(git\s+(checkout\s+(HEAD\s+)?--|restore)|rm|del|Remove-Item)\s", cmd):
        return False
    toks = [t.strip("'\"").replace("\\", "/") for t in cmd.split()[1:] if re.search(r"[/\\]|\.\w+$", t)]
    return bool(toks) and all(t in viol for t in toks)


def decide_shell(role: str, cmd: str, base: Path, cwd: Path):
    if "kb-guard" in cmd or re.search(r"guard\.py['\"]?\s+(clear|manifest)", cmd):
        return WHY["guard"]
    if restoring_violations(base, cmd):
        return None
    # '>' or '|' inside a quoted argument (a search query, "<team>.<domain>") is text, not a redirect
    unquoted = re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: m.group(0).replace(">", " ").replace("|", " "), cmd)
    for t in re.findall(REDIRECT, unquoted):
        if t in ("/dev/null", "nul", "$null", "&1", "&2") or t.startswith("&"):
            continue
        r = rel(t, base, cwd)
        msg = decide_file(role, r, (base / r).exists(), "Bash")
        if msg:
            return f"redirect into {r}: {msg}"
    if GIT_COMMIT.search(re.sub(r"'[^']*'|\"[^\"]*\"", '""', cmd)):  # a quoted "git commit" is text
        return ('agents commit only with `uv run tools/kb.py commit -m "kb: <what>"` (it runs the gate and stages exactly '
                "the reviewed tree). The owner can still use git in their own terminal.")
    return None


# ---------- manifest (post-command backstop) ----------
def tracked_files(base: Path):
    out = {}
    for top in TRACKED_DIRS:
        d = base / top
        if d.exists():
            for p in d.rglob("*"):
                if p.is_file() and "__pycache__" not in p.parts:
                    out[p.relative_to(base).as_posix()] = p
    for f in TRACKED_FILES:
        if (base / f).is_file():
            out[f] = base / f
    return out


def digest(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def snapshot(base: Path, old=None):
    old, snap = old or {}, {}
    for r, p in tracked_files(base).items():
        st = p.stat()
        o = old.get(r)
        snap[r] = o if o and o["size"] == st.st_size and o["mtime"] == st.st_mtime_ns else \
            {"size": st.st_size, "mtime": st.st_mtime_ns, "sha": digest(p)}
    return snap


def write_manifest(base: Path, accept=None):
    """Accept all tracked files (accept=None) or only the given paths into the manifest."""
    sd = state_dir(base, create=True)
    m = load(sd / "manifest.json", {})
    cur = snapshot(base, m)
    if accept is None:
        m = cur
    else:
        for r in accept:
            if r in cur:
                m[r] = cur[r]
            else:
                m.pop(r, None)
    (sd / "manifest.json").write_text(json.dumps(m), encoding="utf-8")


class PurgeSet(set):
    """Purge lines store a hash of the id, so a forgotten subject's name is not kept in a committed file."""
    def __contains__(self, x):
        return set.__contains__(self, x) or set.__contains__(self, purge_hash(x))


def purge_hash(x: str) -> str:
    return "h:" + hashlib.sha1(purge_id(x).encode("utf-8")).hexdigest()[:12]


def purge_id(s: str) -> str:
    """'notes/a.md (claim removed)' or 'a' -> 'a'."""
    s = (s.strip().split() or [""])[0]
    return PurePosixPath(s.replace("\\", "/")).stem


def purged_stems(base: Path):
    f = base / "meta" / "purges.tsv"
    try:
        return PurgeSet(l.split("\t")[1].strip() if l.split("\t")[1].strip().startswith("h:") else purge_id(l.split("\t")[1])
                        for l in f.read_text(encoding="utf-8").splitlines() if l.count("\t") >= 2)
    except OSError:
        return PurgeSet()


def equals_head(base: Path, r: str) -> bool:
    """True if the file now has exactly its committed content (or is absent from both): restoring is never a violation."""
    p = base / r
    try:
        out = subprocess.run(["git", "ls-tree", "HEAD", "--", r], cwd=base, capture_output=True, text=True).stdout.split()
    except OSError:
        return False
    if not p.exists():
        return not out
    if len(out) < 3:
        return False
    data = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == out[2]


def snap_key(data):
    return re.sub(r"[^\w-]", "_", str(data.get("agent_id") or data.get("agent_type") or "main"))[:60]


def post(data):
    """Attribute to this tool call only what changed since its own pre-snapshot; earlier drift (the owner editing
    by hand, another agent) is accepted, not blamed on the caller."""
    role = data.get("agent_type") or "main"
    tool = data.get("tool_name", "Bash")
    base = root(data)
    sd = state_dir(base, create=True)
    m = load(sd / "manifest.json", None)
    if m is None:
        write_manifest(base)
        return 0
    pre_f = sd / f"pre-{snap_key(data)}.json"
    before = load(pre_f, None) or m
    pre_f.unlink(missing_ok=True)
    cur = snapshot(base, before)
    diff = lambda x, y: {r for r in y if r not in x or y[r]["sha"] != x[r]["sha"]} | {r for r in x if r not in y}
    earlier = diff(m, before)  # happened outside this call
    changed = sorted(diff(before, cur))
    purged = purged_stems(base)
    ok = [r for r in changed if may_write(role, r, tool) or equals_head(base, r)
          or (zone(r) in ("user", "sources") and r not in cur and Path(r).stem in purged)]
    bad = [r for r in changed if r not in ok]
    accept = sorted(earlier | set(ok))
    if accept:
        write_manifest(base, accept=accept)
    if not bad:
        return 0
    viol = load(sd / "violations.json", {})
    for r in bad:
        viol[r] = {"role": role, "tool": tool, "bad_sha": cur[r]["sha"] if r in cur else None, "existed": r in before,
                   "command": str((data.get("tool_input") or {}).get("command", ""))[:200]}
    (sd / "violations.json").write_text(json.dumps(viol, indent=1), encoding="utf-8")
    print(f"BLOCKED ({role}, {tool}): this call changed protected files it may not write: {', '.join(bad)}. If you made "
          "the change, run `uv run tools/kb.py restore` (undoes exactly these changes, nothing else) and route the content "
          "the proper way (a new frozen source, or an approved edit of an owner file). If you did not make it, ask the owner. "
          "`kb.py check` fails while the file holds this content.", file=sys.stderr)
    return 2


def pre(data, heartbeat=True):
    role = data.get("agent_type") or "main"
    base = root(data)
    if heartbeat:
        sd = state_dir(base, create=True)
        (sd / "heartbeat").write_text(str(time.time()), encoding="utf-8")
        m = load(sd / "manifest.json", None)
        if m is not None:  # baseline for this call's post check
            (sd / f"pre-{snap_key(data)}.json").write_text(json.dumps(snapshot(base, m)), encoding="utf-8")
    cwd = Path(data.get("cwd") or base)
    tool, ti = data.get("tool_name", ""), data.get("tool_input", {}) or {}
    if tool in ("Bash", "PowerShell"):
        msg = decide_shell(role, str(ti.get("command", "")), base, cwd)
    else:
        path = ti.get("file_path") or ti.get("notebook_path")
        if not path:
            return 0
        r = rel(path, base, cwd)
        msg = decide_file(role, r, (base / r).exists(), tool)
        if msg:
            msg = f"({role} -> {r}): {msg}"
    if msg:
        print(f"BLOCKED {msg}", file=sys.stderr)
        return 2
    return 0


def main():
    for stream in (sys.stdout, sys.stderr):  # hook output is read as UTF-8 (Windows pipes default to the ANSI code page)
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    mode = sys.argv[1] if len(sys.argv) > 1 else "pre"
    if mode == "clear":
        base = root()
        write_manifest(base)
        (state_dir(base) / "violations.json").unlink(missing_ok=True)
        print("guard: current state accepted, violations cleared")
        return 0
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}
    if mode == "manifest":
        write_manifest(root(data))
        return 0
    rc = post(data) if mode == "post" else pre(data)
    if os.environ.get("KB_GUARD_TRACE"):  # opt-in debug trace: one line per hook call
        try:
            ti = data.get("tool_input") or {}
            line = {"t": round(time.time(), 2), "mode": mode, "event": data.get("hook_event_name"),
                    "tool": data.get("tool_name"), "agent": data.get("agent_type") or "main", "rc": rc,
                    "what": str(ti.get("command") or ti.get("file_path") or "")[:160]}
            with open(state_dir(root(data), create=True) / "trace.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(line) + "\n")
        except Exception:
            pass
    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # fail closed
        print(f"BLOCKED: guard error ({type(e).__name__}: {e}). Fix tools/hooks/guard.py or the hook input.", file=sys.stderr)
        sys.exit(2)
