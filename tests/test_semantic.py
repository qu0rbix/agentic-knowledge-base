"""Semantic search with a mock OpenAI-compatible embedding server (no network, no model)."""
import hashlib
import json
import math
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from helpers import make_kb, put, run_kb, source

# the mock "understands" a few synonyms, so a meaning-only match exists without shared words
SYN = {"orbital": "satellite", "orbit": "satellite", "delay": "latency", "lag": "latency", "link": "uplink"}


def vec(text, dim=64):
    v = [0.0] * dim
    for w in text.lower().replace(":", " ").replace(".", " ").split():
        w = SYN.get(w, w)
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dim] += 1
    n = math.sqrt(sum(x * x for x in v)) or 1
    return [x / n for x in v]


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        out = json.dumps({"data": [{"index": i, "embedding": vec(t)} for i, t in enumerate(body["input"])]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


class SemanticScopes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env = {"KB_EMBED_URL": f"http://127.0.0.1:{cls.srv.server_port}/v1", "KB_EMBED_MODEL": "mock"}

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_raw_sources_searchable_by_meaning_when_embedded(self):
        kb = make_kb()
        toml = (kb / "kb.toml").read_text(encoding="utf-8").replace('embed = ["notes", "history"]', 'embed = ["notes", "history", "sources"]')
        (kb / "kb.toml").write_text(toml, encoding="utf-8", newline="\n")
        source(kb, "2026-10-01-quantel", "Quantel satellite uplink latency is 40 ms on the Atlantic route.")
        for i, t in enumerate(["Payroll runs on the last Friday", "Badge access needs a manager form", "The canteen opens at noon"]):
            put(kb, f"notes/n{i}.md", f"---\ntitle: N{i}\ntype: topic\nsummary: s\n---\n- {t}. [src: x §1 \"x\"]\n")
        self.assertEqual(run_kb(kb, "embed", env=self.env).returncode, 0)
        out = run_kb(kb, "search", "orbital link delay", "--in", "sources", env=self.env).stdout
        self.assertIn("2026-10-01-quantel", out)
        self.assertRegex(out, r"match: (semantic|both)")
        self.assertNotIn("quantel", run_kb(kb, "search", "orbital link delay", env=self.env).stdout)  # notes only by default

    def test_unembedded_scope_says_keyword_only(self):
        kb = make_kb()
        source(kb, "2026-10-01-quantel", "Quantel satellite uplink latency is 40 ms.")
        run_kb(kb, "embed", env=self.env)
        out = run_kb(kb, "search", "Quantel", "--in", "sources", env=self.env).stdout
        self.assertIn("does not cover sources", out)
        self.assertIn("2026-10-01-quantel", out)


if __name__ == "__main__":
    unittest.main()
