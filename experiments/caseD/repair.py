"""Undo sessions that only hit the usage limit: remove their .done marker, and the owner-message capture (and pending
entry) the hook saved for that prompt, so the re-run starts from the same state."""
import json, sys
from pathlib import Path

H = Path(__file__).parent
sys.path.insert(0, str(H))
from run_d import SESSIONS

prompts = {n: p for n, p, _ in SESSIONS}
for run in sys.argv[1:]:
    kb, logs = H / "runs" / run / "kb", H / "runs" / run / "logs"
    failed = [f.stem for f in sorted(logs.glob("s*.jsonl")) if "usage_limit_reached" in f.read_text(encoding="utf-8", errors="replace")
              or "hit your 5-hour limit" in f.read_text(encoding="utf-8", errors="replace")]
    failed = [s for s in failed if "." not in s]
    pend_f = kb / ".git" / "kb-guard" / "pending.json"
    pend = json.loads(pend_f.read_text(encoding="utf-8")) if pend_f.exists() else {}
    removed = []
    for s in failed:
        (logs / f"{s}.done").unlink(missing_ok=True)
        (logs / f"{s}.jsonl").rename(logs / f"{s}.limited.jsonl")
        body = prompts[s].strip()
        for f in sorted((kb / "sources" / "user").glob("*.md")):
            t = f.read_text(encoding="utf-8")
            if t.split("\n---\n", 1)[-1].strip() == body and f.stem in pend and not pend[f.stem].get("reminded"):
                f.unlink()
                pend.pop(f.stem, None)
                removed.append(f.name)
                break
    if pend_f.exists():
        pend_f.write_text(json.dumps(pend, indent=1), encoding="utf-8")
    print(run, "failed:", failed, "| captures removed:", len(removed))
