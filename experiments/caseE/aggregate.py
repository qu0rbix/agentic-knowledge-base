import json, re
from pathlib import Path
H = Path(__file__).parent
labels = json.loads((H / "judge/labels.json").read_text(encoding="utf-8"))
auto = json.loads((H / "auto.json").read_text(encoding="utf-8"))
stats = json.loads((H / "stats.json").read_text(encoding="utf-8"))


def val(v):
    if isinstance(v, dict):
        for k in ("status", "result", "verdict", "outcome", "score"):
            if k in v:
                return str(v[k])
        return json.dumps(v)
    return str(v)


def count(d, word):
    items = d.values() if isinstance(d, dict) else d
    return sum(1 for v in items if val(v).lower().startswith(word))


rows = []
for lab, run in sorted(labels.items(), key=lambda x: x[1]):
    s = json.loads((H / f"judge/score_{lab}.json").read_text(encoding="utf-8"))
    r = {"run": run, "label": lab}
    r["facts"] = count(s["facts"], "correct")
    w = s["wrong_current_claims"]
    r["wrong"] = len(w) if isinstance(w, list) else w
    r["claims"] = s.get("total_current_claims")
    if isinstance(r["claims"], dict):
        r["claims"] = next((v for v in r["claims"].values() if isinstance(v, int)), None)
    r["owner_ok"] = count(s["owner"], "ok")
    r["traps"] = count(s["traps"], "held")
    r["answers"] = count(s["answers"], "correct")
    r["reader"] = count(s["reader"], "correct")
    for f, a in s["audits"].items():
        if not isinstance(a, dict) or "plants" not in a:
            continue
        m = re.search(r"(haiku|sonnet)", f, re.I)
        tag = m.group(1).lower() if m else f
        plants = a.get("plants", {})
        validity = a.get("plant_validity", {})
        valid = [p for p in plants if "invalid" not in val(validity.get(p, "")).lower() and "invalid" not in val(plants[p]).lower()]
        found = [p for p in valid if val(plants[p]).lower().startswith("found")]
        contra = [p for p in valid if isinstance(validity.get(p), dict) and validity[p].get("contradicted_in_kb") is True]
        clean = [p for p in valid if p not in contra]
        r[f"{tag}_found"] = f"{len(found)}/{len(valid)}"
        r[f"{tag}_found_uncontradicted"] = f"{len([p for p in clean if p in found])}/{len(clean)}"
        r[f"{tag}_natural"] = f"{len(a.get('natural_errors_found', []))}/{r['wrong']}"
        r[f"{tag}_false"] = len(a.get("false_alarms", []))
        au = auto[run]["audits"].get(f"audit_{tag}", {})
        r[f"{tag}_cost"] = au.get("cost")
    r["prov_located"] = sum(1 for p in s.get("provenance", []) if "locat" in json.dumps(p).lower())
    r["cost"] = auto[run]["cost"]
    r["min"] = auto[run]["minutes"]
    r["words"] = stats[run]["words"]
    r["cite_share"] = stats[run]["citation_char_share"]
    rows.append(r)
keys = list(dict.fromkeys(k for r in rows for k in r))
print("\t".join(keys))
for r in rows:
    print("\t".join(str(r.get(k, "")) for k in keys))
(H / "summary.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
