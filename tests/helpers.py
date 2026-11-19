"""Test helpers: throwaway KBs built from template/, kb.py runner, hook replay (no model needed)."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEMPLATE = REPO / "template"
TODAY = dt.date.today().isoformat()


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDECODE", "KB_EMBED", "KB_RERANK", "CLAUDE_PROJECT_DIR"))}
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra or {})
    return env


def git(kb, *a):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "core.autocrlf=false", *a],
                          cwd=kb, capture_output=True, text=True, encoding="utf-8")


def make_kb(use_git=True):
    kb = Path(tempfile.mkdtemp(prefix="kbtest-")) / "kb"
    shutil.copytree(TEMPLATE, kb, ignore=shutil.ignore_patterns("__pycache__", ".cache", ".kb-guard"))
    if use_git:
        git(kb, "init", "-q")
        git(kb, "config", "user.email", "t@t")
        git(kb, "config", "user.name", "t")
        git(kb, "config", "core.autocrlf", "false")
        commit(kb, "init")
    return kb


def commit(kb, msg="c"):
    git(kb, "add", "-A")
    return git(kb, "commit", "-qm", msg)


def run_kb(kb, *args, env=None):
    return subprocess.run([sys.executable, "tools/kb.py", *args], cwd=kb, capture_output=True, text=True,
                          encoding="utf-8", env=clean_env(env))


def hook(kb, mode, payload, script="guard.py", env=None):
    payload = dict(payload)
    payload.setdefault("cwd", str(kb))
    return subprocess.run([sys.executable, "-I", str(kb / "tools" / "hooks" / script), mode],
                          input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
                          env=clean_env({"CLAUDE_PROJECT_DIR": str(kb), **(env or {})}))


def bash(cmd, role=None, tool="Bash"):
    d = {"tool_name": tool, "tool_input": {"command": cmd}}
    if role:
        d["agent_type"] = role
    return d


def write_tool(path, role=None, tool="Write"):
    d = {"tool_name": tool, "tool_input": {"file_path": path}}
    if role:
        d["agent_type"] = role
    return d


def put(kb, rel, text):
    p = kb / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")
    return p


def source(kb, sid, body, kind="files", date="2026-09-29", sha=True):
    import hashlib
    h = hashlib.sha256(body.rstrip("\n").encode("utf-8")).hexdigest()[:16] if sha else ""
    return put(kb, f"sources/{kind}/{sid}.md", f"---\nid: {sid}\ntype: {kind}\ndate: {date}\ntier: 1\nsha256: {h}\n---\n{body}\n")


def note(kb, nid, claims, title=None, folder="", ntype="process", extra=""):
    rel = f"notes/{folder + '/' if folder else ''}{nid}.md"
    body = "\n".join(f"- {c}" for c in claims)
    return put(kb, rel, f"---\nid: {nid}\ntype: {ntype}\ntitle: {title or nid.replace('-', ' ').title()}\n"
                        f"summary: about {nid}\naliases: []\nstatus: current\nupdated: 2026-10-01\n{extra}---\n"
                        f"## Claims\n{body}\n")
