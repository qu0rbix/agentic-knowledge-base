"""Fetch Node.js release-schedule history (ground truth) and README snapshots (corpus) via gh api."""
import base64, json, subprocess
from pathlib import Path

OUT = Path(__file__).parent / "raw" / "node"
OUT.mkdir(parents=True, exist_ok=True)


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise SystemExit(r.stderr)
    return json.loads(r.stdout)


commits = gh("repos/nodejs/Release/commits?path=schedule.json&per_page=100")
hist = []
for c in commits:
    sha, date = c["sha"], c["commit"]["author"]["date"][:10]
    if not ("2019-06-01" <= date <= "2023-12-31"):
        continue
    f = gh(f"repos/nodejs/Release/contents/schedule.json?ref={sha}")
    hist.append({"sha": sha, "date": date, "msg": c["commit"]["message"].split("\n")[0],
                 "schedule": json.loads(base64.b64decode(f["content"]))})
    try:
        r = gh(f"repos/nodejs/Release/contents/README.md?ref={sha}")
        (OUT / f"{date}-readme-{sha[:7]}.md").write_text(base64.b64decode(r["content"]).decode("utf-8"), encoding="utf-8")
    except SystemExit:
        pass
(OUT / "schedule_history.json").write_text(json.dumps(sorted(hist, key=lambda h: h["date"]), indent=1), encoding="utf-8")
print(len(hist), "schedule versions")
