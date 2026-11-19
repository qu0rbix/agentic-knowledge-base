# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Create a new knowledge base from the agentic-knowledge-base template - with NO link to the template repo.

    uv run https://raw.githubusercontent.com/qu0rbix/agentic-knowledge-base/main/scripts/create_kb.py my-kb

Downloads the template archive, copies only template/ into <target>, runs `git init` and makes a first
commit. No remote is configured: add your own with `git remote add origin <your-repo-url>`.
Options: --ref <branch|tag> (default main), --no-git.
"""
import argparse, io, shutil, subprocess, sys, tarfile, tempfile, urllib.request
from pathlib import Path

REPO = "qu0rbix/agentic-knowledge-base"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--no-git", action="store_true")
    a = ap.parse_args()
    target = Path(a.target).resolve()
    if target.exists() and any(target.iterdir()):
        sys.exit(f"{target} exists and is not empty")
    url = f"https://codeload.github.com/{REPO}/tar.gz/{a.ref}"
    print(f"downloading {url}")
    try:
        data = urllib.request.urlopen(url, timeout=60).read()
    except Exception as e:  # private/hidden repo or rate limit: fall back to an authenticated gh CLI
        if not shutil.which("gh"):
            sys.exit(f"download failed ({e}); install/login the GitHub CLI (gh) or check the repo is public")
        print(f"anonymous download failed ({e}); using gh api")
        r = subprocess.run(["gh", "api", f"repos/{REPO}/tarball/{a.ref}"], capture_output=True)
        if r.returncode != 0:
            sys.exit("gh api failed: " + r.stderr.decode("utf-8", "replace").strip()
                     + " - run `gh auth login`, or check the repo/ref exists and you have access.")
        data = r.stdout
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
            members = [m for m in tf.getmembers() if "/template/" in m.name + "/" and ".." not in m.name]
            tf.extractall(tmp, members=members, filter="data")
        src = next(Path(tmp).glob("*/template"))
        shutil.copytree(src, target, dirs_exist_ok=True)
    # version stamp + hashes of every scaffold file, so a future upgrade can tell owner edits from stock files
    import hashlib, json as _json, datetime as _dt
    files = {q.relative_to(target).as_posix(): hashlib.sha256(q.read_bytes()).hexdigest()
             for q in target.rglob("*") if q.is_file()}
    (target / ".akb").mkdir(exist_ok=True)
    (target / ".akb" / "version.json").write_text(_json.dumps(
        {"template_ref": a.ref, "created": _dt.date.today().isoformat(), "files": files}, indent=1), encoding="utf-8")
    print(f"created {target}")
    if not a.no_git and shutil.which("git"):
        run = lambda *c: subprocess.run(["git", *c], cwd=target, check=True, capture_output=True)
        run("init", "-q")
        run("config", "core.longpaths", "true")
        run("add", "-A")
        c = subprocess.run(["git", "commit", "-qm", "New knowledge base from agentic-knowledge-base template"],
                           cwd=target, capture_output=True, text=True)
        if c.returncode == 0:
            print("git repo initialised with a first commit (no remote). Add yours: git remote add origin <url>")
        else:
            print("git repo initialised and files staged, but the first commit failed:\n  " + c.stderr.strip()
                  + "\n  Set your identity (git config --global user.name/user.email), then: git commit -m 'New KB'")
    print(f'next:  cd "{target}"  &&  claude      then say: "set up this KB"')


if __name__ == "__main__":
    main()
