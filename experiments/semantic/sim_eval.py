"""Evaluate kb.find_similar on extra.json 'similar' items (run from the benchmark KB root)."""
import json, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
import kb

items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["similar"]
stats = defaultdict(lambda: [0, 0, 0])  # hit, n, numbers-differ flagged
for it in items:
    found = kb.find_similar(it["text"])
    refs = {ref for kind, ref, raw, d in found}
    s = stats[it["kind"]]
    s[1] += 1
    if it["expected"]:
        s[0] += bool(refs & set(it["expected"]))
        s[2] += any(ref in it["expected"] and kb.numbers(it["text"]) and kb.numbers(raw) and kb.numbers(it["text"]) != kb.numbers(raw)
                    for kind, ref, raw, d in found)
    else:
        s[0] += bool(found)  # distractor: any hit is a (soft) false alarm
e = kb.engine(lazy=False)
print("mode:", "keyword overlap + vectors" if e and "off" not in e else "keyword overlap only")
for k, (h, n, nd) in sorted(stats.items()):
    label = "shown (false alarms)" if k == "distractor" else "expected note in top 3"
    print(f"  {k:10} {label}: {h}/{n}" + (f"   NUMBERS DIFFER flagged: {nd}" if k == "conflict" else ""))
