"""kbsem - optional semantic layer for kb.py (bring your own key or a local server). Stdlib only.

Configured through OS environment variables or `~/.config/akb/env` (outside the KB, so agents cannot repoint it);
the KB's own `.env` is NOT read:
  KB_EMBED_URL           base URL of an OpenAI-compatible API, e.g. https://api.voyageai.com/v1,
                         https://api.openai.com/v1, http://localhost:1234/v1 (LM Studio), http://localhost:11434/v1 (Ollama)
  KB_EMBED_MODEL         a pinned, versioned model name
  KB_EMBED_KEY           API key (not needed for local servers). Never printed.
  (Use a strong model; after choosing one, calibrate: `kb.py search-eval eval/golden.md --calibrate`.)
  KB_EMBED_QUERY_PREFIX  / KB_EMBED_DOC_PREFIX  for asymmetric models
                         (nomic-embed-text: "search_query: " / "search_document: "; e5: "query: " / "passage: ")
Optional reranker (second stage, reorders the top ~30 hits; any Cohere/Voyage/Jina/llama.cpp-style endpoint):
  KB_RERANK_URL          FULL endpoint URL, e.g. https://api.voyageai.com/v1/rerank, https://api.cohere.com/v2/rerank,
                         https://api.jina.ai/v1/rerank, http://localhost:8080/v1/rerank (llama-server --reranking)
  KB_RERANK_MODEL        e.g. rerank-2.5, rerank-v3.5, jina-reranker-v2-base-multilingual, qwen3-reranker
  KB_RERANK_KEY          API key (not needed for local servers). Never printed.
Vectors live in `.cache/embeddings.sqlite` (git-ignored), keyed by a hash of model + prefixes + text.
"""
import array, hashlib, json, math, os, re, sqlite3, time, urllib.error, urllib.request
from operator import mul
from pathlib import Path

BATCH = 64
CANARY = "kb canary: approvals for production changes are recorded in the change log"
PREFIX_MODELS = re.compile(r"nomic|e5|bge|gte|arctic", re.I)


def _read(root: Path, keys):
    cfg = {}
    # deliberately NOT the KB's own .env: an agent (or injected text) could repoint the endpoint and exfiltrate notes
    for f in (Path.home() / ".config" / "akb" / "env",):
        if f.exists():
            for line in f.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\s*(KB_[A-Z_]+)\s*=\s*(.*)$", line)
                if m and m.group(1) in keys:
                    v = m.group(2).strip()
                    cfg[m.group(1)] = v[1:-1] if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"" else v
    for k in keys:
        if os.environ.get(k) is not None:
            cfg[k] = os.environ[k]
    return cfg


def rerank_config(root: Path):
    cfg = _read(root, ("KB_RERANK_URL", "KB_RERANK_MODEL", "KB_RERANK_KEY"))
    if not cfg.get("KB_RERANK_URL") or not cfg.get("KB_RERANK_MODEL"):
        return None
    cfg["KB_EMBED_KEY"] = cfg.get("KB_RERANK_KEY")  # so _redact hides it
    cfg["fingerprint"] = cfg["KB_RERANK_URL"] + "|" + cfg["KB_RERANK_MODEL"]
    return cfg


def rerank(cfg, query, docs):
    """Relevance score per document (same order). Accepts `results` (Cohere/Jina/llama.cpp) or `data` (Voyage)."""
    body = json.dumps({"model": cfg["KB_RERANK_MODEL"], "query": query, "documents": docs}).encode()
    req = urllib.request.Request(cfg["KB_RERANK_URL"], data=body, headers={"Content-Type": "application/json", "User-Agent": "kb-rerank"})
    if cfg.get("KB_RERANK_KEY"):
        req.add_header("Authorization", "Bearer " + cfg["KB_RERANK_KEY"])
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise EmbedError(_redact(f"HTTP {e.code} from rerank API: {e.read()[:200]!r}", cfg))
        except (urllib.error.URLError, OSError, ValueError) as e:
            if attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise EmbedError(_redact(f"rerank API unreachable: {e}", cfg))
    rows = data.get("results", data.get("data")) if isinstance(data, dict) else data
    scores = [None] * len(docs)
    for r in rows or []:
        i = r.get("index")
        s = r.get("relevance_score", r.get("score"))
        if isinstance(i, int) and 0 <= i < len(docs) and s is not None:
            scores[i] = float(s)
    if any(s is None for s in scores):
        raise EmbedError("rerank API did not return a score for every document")
    return scores


def config(root: Path):
    keys = ("KB_EMBED_URL", "KB_EMBED_MODEL", "KB_EMBED_KEY", "KB_EMBED_QUERY_PREFIX", "KB_EMBED_DOC_PREFIX")
    cfg = _read(root, keys)
    if not cfg.get("KB_EMBED_URL") or not cfg.get("KB_EMBED_MODEL"):
        return None
    cfg["fingerprint"] = "|".join(cfg.get(k, "") for k in ("KB_EMBED_URL", "KB_EMBED_MODEL", "KB_EMBED_QUERY_PREFIX", "KB_EMBED_DOC_PREFIX"))
    return cfg


def warnings(cfg):
    out = []
    if PREFIX_MODELS.search(cfg["KB_EMBED_MODEL"]) and not (cfg.get("KB_EMBED_QUERY_PREFIX") or cfg.get("KB_EMBED_DOC_PREFIX")):
        out.append(f"model '{cfg['KB_EMBED_MODEL']}' usually needs KB_EMBED_QUERY_PREFIX/KB_EMBED_DOC_PREFIX - quality drops silently without them")
    return out


class EmbedError(Exception):
    pass


def _redact(s: str, cfg) -> str:
    k = cfg.get("KB_EMBED_KEY")
    return s.replace(k, "***") if k else s


def embed(cfg, texts, query=False):
    """Normalised vectors for texts (adds the query/doc prefix). Raises EmbedError (key redacted)."""
    prefix = cfg.get("KB_EMBED_QUERY_PREFIX" if query else "KB_EMBED_DOC_PREFIX", "")
    out = []
    for i in range(0, len(texts), BATCH):
        body = json.dumps({"model": cfg["KB_EMBED_MODEL"], "input": [prefix + t for t in texts[i:i + BATCH]]}).encode()
        req = urllib.request.Request(cfg["KB_EMBED_URL"].rstrip("/") + "/embeddings", data=body,
                                     headers={"Content-Type": "application/json", "User-Agent": "kb-embed"})
        if cfg.get("KB_EMBED_KEY"):
            req.add_header("Authorization", "Bearer " + cfg["KB_EMBED_KEY"])
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    data = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise EmbedError(_redact(f"HTTP {e.code} from embedding API: {e.read()[:200]!r}", cfg))
            except (urllib.error.URLError, OSError, ValueError) as e:
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise EmbedError(_redact(f"embedding API unreachable: {e}", cfg))
        rows = sorted(data.get("data", []), key=lambda d: d.get("index", 0))
        if len(rows) != len(texts[i:i + BATCH]):
            raise EmbedError("embedding API returned a different number of vectors than requested")
        for d in rows:
            v = d["embedding"]
            n = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / n for x in v])
    return out


def dot(a, b):
    return sum(map(mul, a, b))


def zscores(scores):
    if len(scores) < 2:
        return [0.0] * len(scores)
    m = sum(scores) / len(scores)
    sd = math.sqrt(sum((s - m) ** 2 for s in scores) / len(scores)) or 1e-9
    return [(s - m) / sd for s in scores]


class Store:
    def __init__(self, root: Path, cfg):
        self.cfg = cfg
        d = root / ".cache"
        d.mkdir(exist_ok=True)
        self.db = sqlite3.connect(d / "embeddings.sqlite", timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS vec (key TEXT PRIMARY KEY, kind TEXT, ref TEXT, dim INT, v BLOB)")
        self.db.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")

    @staticmethod
    def key(cfg, text):
        return hashlib.sha1((cfg["fingerprint"] + "\x00" + text).encode("utf-8")).hexdigest()

    def meta(self, k, v=None):
        if v is None:
            r = self.db.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
            return r[0] if r else None
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
        self.db.commit()

    def missing(self, units):
        have = {r[0] for r in self.db.execute("SELECT key FROM vec")}
        return [u for u in units if u["key"] not in have]

    def prune(self, keys):
        keep = set(keys)
        gone = [r[0] for r in self.db.execute("SELECT key FROM vec") if r[0] not in keep]
        self.db.executemany("DELETE FROM vec WHERE key=?", [(k,) for k in gone])
        self.db.commit()
        return len(gone)

    def canary_ok(self):
        """Detects a provider silently changing the model behind the same name."""
        v = embed(self.cfg, [CANARY])[0]
        k = "canary:" + self.cfg["fingerprint"]
        old = self.meta(k)
        self.meta(k, json.dumps(v))
        return old is None or dot(json.loads(old), v) >= 0.99

    def sync(self, units, limit=None):
        """Embed missing units (all if limit is None). Returns (embedded, still_missing)."""
        todo = self.missing(units)
        if limit is not None and len(todo) > limit:
            return 0, len(todo)
        dims = set()
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            vecs = embed(self.cfg, [u["text"] for u in chunk])
            dims |= {len(v) for v in vecs}
            self.db.executemany("INSERT OR REPLACE INTO vec VALUES (?,?,?,?,?)",
                                [(u["key"], u["kind"], u["ref"], len(v), array.array("f", v).tobytes()) for u, v in zip(chunk, vecs)])
            self.db.commit()  # cache every batch
        if len(dims) > 1:
            raise EmbedError(f"embedding API returned vectors of different lengths {sorted(dims)}")
        return len(todo), 0

    def vectors(self, keys):
        out = {}
        q = "SELECT key, v FROM vec WHERE key IN (%s)"
        keys = list(keys)
        for i in range(0, len(keys), 500):
            part = keys[i:i + 500]
            for k, b in self.db.execute(q % ",".join("?" * len(part)), part):
                out[k] = array.array("f", b)  # compact: ~4 bytes per dimension instead of a Python float list
        return out
