"""Summarise a session log: tool calls, blocks, subagents, final text, cost."""
import json, sys
from pathlib import Path

for name in sys.argv[1:]:
    p = Path(__file__).parent / "logs" / f"{name}.jsonl"
    print(f"##### {name}")
    for l in p.open(encoding="utf-8"):
        try:
            d = json.loads(l)
        except ValueError:
            print("RAW", l[:200].rstrip()); continue
        t = d.get("type")
        sub = " [sub]" if d.get("parent_tool_use_id") else ""
        if t == "assistant":
            for c in d["message"]["content"]:
                if c["type"] == "tool_use":
                    i = c["input"]
                    what = i.get("command") or i.get("file_path") or i.get("subagent_type") or i.get("skill") or ""
                    print(f"USE{sub} {c['name']}: {str(what)[:170]}")
                elif c["type"] == "text" and not sub:
                    print("TXT", c["text"][:600].replace("\n", " | "))
        elif t == "user" and isinstance(d["message"]["content"], list):
            for c in d["message"]["content"]:
                if c.get("type") == "tool_result":
                    s = str(c.get("content"))
                    if c.get("is_error") or "BLOCKED" in s or "VIOLATION" in s.upper():
                        print(f"ERR{sub}", s[:300].replace("\n", " | "))
        elif t == "result":
            print("RESULT", d.get("subtype"), "cost", d.get("total_cost_usd"), "turns", d.get("num_turns"),
                  "denials", len(d.get("permission_denials") or []))
            for x in d.get("permission_denials") or []:
                print("  DENIED", x["tool_name"], str(x["tool_input"])[:150])
