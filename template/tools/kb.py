#!/usr/bin/env python3
"""kb - deterministic helper for the knowledge base. Stdlib only. Run from the KB root.

Anyone:
  uv run tools/kb.py check [--inbox]        validate notes (and inbox candidates); 0 problems = clean
  uv run tools/kb.py verify [--all] [ids...]   evidence pack: each new/changed (or, with --all, every) claim next to its source text
  uv run tools/kb.py precheck               does the uncommitted change need the reviewer? (only pure moves skip)
  uv run tools/kb.py search "<query>" [--in notes,history,sources,reports,inbox,work,meta,data | --all] [--keyword] [-k N]
  uv run tools/kb.py similar "<claim text>"   existing claims (current + superseded) that may state the same fact
  uv run tools/kb.py embed                  build/check embeddings (optional semantic search + reranker, see tools/kbsem.py)
  uv run tools/kb.py search-eval <file> [--calibrate]   recall of keyword vs hybrid search
  uv run tools/kb.py links <id>             outlinks and backlinks of a note
  uv run tools/kb.py stats [--since 7d] [--stale [--today D]]   counts, hints, pending items; --stale lists stale claims
  uv run tools/kb.py freeze <file> --kind files|meetings|email|chat [--tier N] [--title T]   byte-exact source copy
  uv run tools/kb.py forget-check <words...>   where forgotten words still occur (no logging)
  uv run tools/kb.py commit -m "kb: <what>"   the only way to commit: check clean (+ review if kb.toml says always), then commit
  uv run tools/kb.py coverage <source-id> [--top N]   ingest recall aid: uncovered sentences, most fact-like first
  uv run tools/kb.py restore                undo exactly the changes the guard flagged
Notes and structure:
  uv run tools/kb.py forget <ids...> --reason owner-request|filed-by-mistake|private|never-true [--words w...]
  uv run tools/kb.py new <type> <id> --title "..." --summary "..."
  uv run tools/kb.py mv <id> <folder>       move a note into notes/<folder>/ (id and links unchanged)
  uv run tools/kb.py archive <id> --reason "..."

Citations: [src: <source-id> <locator> "exact quote"] | [src: user YYYY-MM-DD "owner's exact words"]
Every number in a claim must appear in one of its quotes. Quotes >= 12 characters. Links: [[note-id]]
"""
import argparse, datetime as dt, hashlib, json, os, re, sqlite3, subprocess, sys, time, unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()
NOTES, HISTORY, ARCHIVE, SOURCES, INBOX, META = (ROOT / d for d in ("notes", "history", "archive", "sources", "inbox", "meta"))
REQUIRED = ["id", "type", "title", "summary", "status", "updated"]
def load_config():
    try:
        import tomllib
        return tomllib.loads((ROOT / "kb.toml").read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return {}


CFG = load_config()
TYPES = set(CFG.get("notes", {}).get("types") or
            ["process", "system", "person", "team", "vendor", "decision", "preference", "topic", "method", "dataset"])
_RD = CFG.get("notes", {}).get("review_days") or {}
REVIEW_DAYS = {k: int(v) for k, v in _RD.items() if k != "default"}
DEFAULT_REVIEW = int(_RD.get("default", 180))
CIT = re.compile(r'\[src:\s*([^\]\s"]+)((?:"[^"]*"|[^\]"])*)\]')  # a quote may contain "]" (markdown tables, links)
QUOTE = re.compile(r'"([^"]+)"')
LINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STAMP = re.compile(r"\b(?:as of|since|per|from)\s+(\d{4}-\d{2}-\d{2})", re.I)  # removed before number checks
FRESH = re.compile(r"\bas of\s+(\d{4}-\d{2}-\d{2})", re.I)  # only "as of" says when a claim was true
NUM = re.compile(r"\d[\d,.]*")
BULLET = re.compile(r"^\s*[-*+]\s+")
FENCE = re.compile(r"^[ \t]+(```|~~~)")              # an example block: fenced, indented under its claim bullet
FOOT_DEF = re.compile(r"^\[\^([\w-]+)\]:\s*(.*)$")   # [^id]: [src: ...]
FOOT_REF = re.compile(r"\[\^([\w-]+)\]")
LINK_HEADINGS = re.compile(r"^#+\s*(related|see also|links|members|contents|notes in this hub)\b", re.I)
HIST_HEAD = re.compile(r"^## Superseded \d{4}-\d{2}-\d{2}\b")
MIN_QUOTE = 12
EMBED_SCOPES = list(CFG.get("search", {}).get("embed", ["notes", "history"]))  # what semantic search covers
MISSES = ROOT / ".cache" / "search-misses.log"  # untracked: queries can hold forgotten words
STOP = set("a an and are as at be by can did do does for from has have how i in is it its me my of on or our "
           "should that the their there this to was we what when where which who why will with you your "
           "de het een en van voor wat wie hoe is zijn".split())


# ---------------- parsing ----------------
def parse(path: Path):
    return parse_text(path.read_text(encoding="utf-8"))


def parse_text(text: str):
    fm, body = {}, text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    v = v.strip()
                    if v.startswith("[") and "]" in v:
                        v = [x.strip().strip("'\"") for x in v[1:v.rindex("]")].split(",") if x.strip()]
                    elif v[:1] in "'\"" and v[:1] and v.count(v[0]) >= 2:
                        v = v[1:v.index(v[0], 1)]
                    else:
                        v = re.sub(r"\s+#.*$", "", v).strip()
                    fm[k.strip()] = v
            body = text[end + 4:]
    return fm, body


def claims(body: str, blocks=None):
    """[(in_link_section, text)] - bullets with their indented continuation lines joined. A footnote marker is replaced
    by its definition, so every caller sees inline citations. A fenced block indented under a bullet is an example,
    not claim text: returned through `blocks` as (claim text, code)."""
    lines = body.splitlines()
    defs = {m.group(1): m.group(2) for m in map(FOOT_DEF.match, lines) if m}
    out, link_sec, cur, fence, found = [], False, None, None, []
    for line in lines:
        if fence is not None:
            if FENCE.match(line):
                fence = None
            else:
                fence.append(line)
            continue
        if cur is not None and FENCE.match(line):
            fence = []
            found.append((cur, fence))
            continue
        if line.startswith("#"):
            link_sec = bool(LINK_HEADINGS.match(line))
            cur = None
            continue
        if BULLET.match(line):
            cur = [link_sec, BULLET.sub("", line).strip()]
            out.append(cur)
        elif cur is not None and line.strip() and line[:1] in " \t":
            cur[1] += " " + line.strip()
        else:
            cur = None
    for c in out:
        c[1] = FOOT_REF.sub(lambda m: " " + defs.get(m.group(1), f"[src: MISSING-FOOTNOTE-{m.group(1)}]"), c[1])
    if blocks is not None:
        blocks += [(c[1], "\n".join(code)) for c, code in found]
    return [tuple(c) for c in out]


def norm(s: str) -> str:
    s = FOOT_REF.sub(" ", CIT.sub(" ", s))
    s = re.sub(r"[^\w]+", " ", s.lower())
    return " ".join(s.split())


# every quotation mark in any script is dropped, dashes -> -, invisible characters removed (language-free quote matching)
_QMARKS = "\"'`\u00ab\u00bb\u2018\u2019\u201a\u201b\u201c\u201d\u201e\u201f\u2039\u203a\u2032\u2033\u300c\u300d\u300e\u300f\uff02\uff07"
_WS_TABLE = {ord(c): None for c in _QMARKS}
_WS_TABLE.update({c: None for c in range(0x2000, 0x2e80) if unicodedata.category(chr(c)) in ("Pi", "Pf")})
_WS_TABLE.update({c: "-" for c in range(0x2010, 0x2016)} | {0x2212: "-", 0xfe58: "-", 0xfe63: "-", 0xff0d: "-"})
_WS_TABLE.update({c: None for c in (0x00ad, 0x200b, 0x200c, 0x200d, 0x2060, 0xfeff)})


def wsnorm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s).translate(_WS_TABLE)
    s = re.sub(r"[*_|]+", " ", s)  # markdown emphasis/table pipes from converted pages
    s = re.sub(r"\s+([:;?!.,)\]])", r"\1", " ".join(s.split()))  # "jours :" (French spacing) == "jours:"
    return s.casefold()


# identifiers are numbers GLUED to letters or symbols (INC-2291, v4.2, Q3, §3, #4): language-free. "Orion 4.2" or
# "Abschnitt 4" are not identifiers - a claim stating such a number quotes the passage that holds it.
IDENT = re.compile(r"(?:\b[^\W\d_]+[-_]?|§\s*|#)\d[\d.,]*")
# date-shaped tokens in any language: 2026-12-31, 31.12.2026, 31/12/26, "31 December 2026", "12. März 2026", "March 12, 2026"
DATE_SHAPES = re.compile(r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}[./-]\d{1,2}[./-](?:\d{4}|\d{2})\b"
                         r"|\b\d{1,2}(?:st|nd|rd|th|er|e)?\.?\s+[^\W\d_]{3,}\.?,?\s+(?:19|20)\d{2}\b"
                         r"|\b[^\W\d_]{3,}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+(?:19|20)\d{2}\b")
ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
NUMTOK = re.compile(r"\d+(?:[.,]\d+|['\u2019\u00a0\u2009\u202f]\d{3}(?!\d))*")


def _readings(tok: str) -> set:
    """The values a written number can mean. '3,5' -> {3.5}; '1.05' -> {1.05}; '1,204' and '1.204' -> {1204, 1.204};
    '1.234.567,89' -> {1234567.89}; zeros after a decimal point are never dropped (1.05 != 1.5)."""
    tok = re.sub(r"['\u2019\u00a0\u2009\u202f]", "", tok)
    parts, seps = re.split(r"[.,]", tok), re.findall(r"[.,]", tok)
    z = lambda d: d.lstrip("0") or "0"
    if not seps:
        return {z(tok)}
    out = set()
    grouped = 1 <= len(parts[0]) <= 3 and all(len(x) == 3 for x in parts[1:])
    if grouped and len(set(seps)) == 1:
        out.add(z("".join(parts)))
    head, frac = parts[:-1], parts[-1]
    if seps[-1] not in seps[:-1] and (len(head) == 1 or (1 <= len(head[0]) <= 3 and all(len(x) == 3 for x in head[1:]))):
        f = frac if (grouped and len(set(seps)) == 1) else frac.rstrip("0")  # 4,000 never equals 4
        out.add(z("".join(head)) + ("." + f if f else ""))
    return out or {".".join(z(x) for x in parts)}


def numbers(s: str, known: str = None) -> dict:
    """Quantities in a text as {written token: possible values}. Dates (any notation) are not quantities. Glued
    identifiers (INC-2291, v4.2, §3) are not quantities - in a claim only if the identical token is in its cited source
    (`known`, wsnorm'ed); otherwise their digits are checked like any number (USD900 vs USD500)."""
    for rx in (CIT, STAMP, LINK, DATE_SHAPES):
        s = rx.sub(" ", s)
    keep = lambda m: " " if known is None or wsnorm(m.group(0)) in known else " " + re.sub(r"^\D+", "", m.group(0)) + " "
    s = IDENT.sub(keep, s)
    return {t: _readings(t) for t in NUMTOK.findall(s)}


def date_keys(s: str) -> set:
    """(year, month or None, day) for every date-shaped token; d/m/y forms give both readings."""
    out = set()
    for tok in DATE_SHAPES.findall(s):
        n = [int(x) for x in re.findall(r"\d+", tok)]
        if re.match(r"\d{4}-", tok):
            out.add((n[0], n[1], n[2]))
        elif re.match(r"\d{1,2}[./-]\d{1,2}[./-]", tok):
            y = n[2] + 2000 if n[2] < 100 else n[2]
            out |= {(y, n[1], n[0]), (y, n[0], n[1])}
        else:  # a month written as a word: year and day must match, the month is the reviewer's to read
            out.add((n[-1], None, n[0]))
    return out


def unsupported_dates(claim: str, quotes) -> list:
    """ISO dates stated in a claim (not 'as of/since' stamps) that no quote states in any notation."""
    c = STAMP.sub(" ", CIT.sub(" ", claim))
    have = set().union(*(date_keys(q) for q in quotes)) if quotes else set()
    bad = []
    for y, m, d in ((int(a), int(b), int(c_)) for a, b, c_ in ISO.findall(c)):
        if not any(hy == y and hd == d and hm in (None, m) for hy, hm, hd in have):
            bad.append(f"{y:04d}-{m:02d}-{d:02d}")
    return bad


def num_missing(a: dict, b: dict) -> list:
    """Tokens of a whose every reading is absent from b."""
    rb = set().union(*b.values()) if b else set()
    return sorted(t for t, r in a.items() if not r & rb)


def md_files(d: Path):
    return sorted(p for p in d.rglob("*.md")) if d.exists() else []


def source_ids():
    return {p.stem: p for p in md_files(SOURCES)}


def redirects():
    r, f = {}, ROOT / "redirects.tsv"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "\t" in line and not line.startswith("#"):
                a, b = line.split("\t", 1)
                r[a.strip()] = b.strip()
    return r


def note_files():
    return md_files(NOTES)


def note_ids():
    return {p.stem: p for p in note_files()}


def git(*a, inp=None):
    if not (ROOT / ".git").exists():
        return ""
    try:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                              input=inp).stdout
    except OSError:
        return ""


def has_head():
    return bool(git("rev-parse", "--verify", "-q", "HEAD").strip())


def head_texts(*dirs):
    """{path: text} of .md files under dirs at HEAD (one git call)."""
    if not has_head():
        return {}
    paths = [p for p in git("ls-tree", "-r", "--name-only", "HEAD", "--", *dirs).splitlines() if p.endswith(".md")]
    if not paths:
        return {}
    raw = subprocess.run(["git", "cat-file", "--batch"], cwd=ROOT, capture_output=True,
                         input="".join(f"HEAD:{p}\n" for p in paths).encode()).stdout
    out, i = {}, 0
    for p in paths:
        nl = raw.index(b"\n", i)
        size = int(raw[i:nl].split()[2])
        out[p] = raw[nl + 1:nl + 1 + size].decode("utf-8", "replace")
        i = nl + 1 + size + 1
    return out


def body_of(text: str):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def purged_ids():
    """ids listed in uncommitted lines of meta/purges.tsv (the forget flow)."""
    f = META / "purges.tsv"
    if not f.exists():
        return PurgeSet()
    if has_head() and git("ls-files", "meta/purges.tsv").strip():
        lines = [l[1:] for l in git("diff", "HEAD", "--", "meta/purges.tsv").splitlines()
                 if l.startswith("+") and not l.startswith("+++")]
    else:
        lines = f.read_text(encoding="utf-8").splitlines()
    return PurgeSet(l.split("\t")[1].strip() if l.split("\t")[1].strip().startswith("h:") else purge_id(l.split("\t")[1])
                    for l in lines if l.count("\t") >= 2)


class PurgeSet(set):
    """meta/purges.tsv stores a hash of each id, so a forgotten subject's name is not kept in a committed file."""
    def __contains__(self, x):
        return set.__contains__(self, x) or set.__contains__(self, purge_hash(x))


def purge_hash(x):
    return "h:" + hashlib.sha1(purge_id(x).encode("utf-8")).hexdigest()[:12]


def purge_id(s):
    """'notes/a.md (claim removed)' or 'a' -> 'a'."""
    s = (s.strip().split() or [""])[0]
    return Path(s.replace("\\", "/")).stem


# ---------------- citations ----------------
_src_cache = {}


def source_body(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---\n", 3)
        if end != -1:
            return text[end + 5:]
    return text


def src_text(p: Path):
    if p not in _src_cache:
        _src_cache[p] = wsnorm(source_body(p.read_text(encoding="utf-8")))  # quotes must come from the body, not frontmatter
    return _src_cache[p]


def user_files(date: str):
    return sorted((SOURCES / "user").glob(f"{date}*.md")) if (SOURCES / "user").exists() else []


def guard_state() -> Path:
    return (ROOT / ".git" / "kb-guard") if (ROOT / ".git").is_dir() else (ROOT / ".kb-guard")


def load_state(name, default):
    try:
        return json.loads((guard_state() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_state(name, data):
    d = guard_state()
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(json.dumps(data, indent=1), encoding="utf-8")


def cited_user_files() -> set:
    """sources/user files that hold the quote of some [src: user ...] citation in notes/ or inbox/ (incl. processed)."""
    quotes = []
    for d in (NOTES, INBOX):
        for p in md_files(d):
            for m in CIT.finditer(p.read_text(encoding="utf-8")):
                if m.group(1) == "user":
                    rest = m.group(2).strip()
                    day = rest.split()[0] if rest else ""
                    quotes += [(day, wsnorm(q)) for q in QUOTE.findall(rest) if len(q.strip()) >= MIN_QUOTE]
    out = set()
    for day, q in quotes:
        for f in user_files(day) if DATE.match(day) else []:
            if q in src_text(f):
                out.add(f.relative_to(ROOT).as_posix())
    return out


PASTE_HINTS = re.compile(r"(?m)^(>.*\n){2,}|^[^\s:]{2,20}:\s.+\n[^\s:]{2,20}:\s.+|https?://")


def looks_pasted(text: str) -> bool:
    """Language-free hint that an owner message carries forwarded/pasted material (quote block, header block, URL, long)."""
    return len(text) > 1500 or text.strip().count("\n") >= 3 or bool(PASTE_HINTS.search(text))


def check_evidence(claim: str, cites: str, srcs, where: str, problems):
    """claim = statement text; cites = text holding its [src: ...] citations. A source citation is an id plus an
    optional locator (no quote: a verbatim quote makes later reviews confirm the quote instead of asking whether a newer
    source changed the fact - case E). Owner citations keep the owner's words as a quote. Every number and date in the
    claim must appear in a cited source (any notation for dates); a quote that IS given must be exact."""
    quotes = []
    for m in CIT.finditer(cites):
        sid, rest = m.group(1), m.group(2)
        qs = QUOTE.findall(rest)
        for q in qs:
            if len(q.strip()) < MIN_QUOTE:
                problems.append(f"{where}: quote shorter than {MIN_QUOTE} characters: \"{q}\" (quote enough to show the context)")
        if sid == "observed":
            problems.append(f"{where}: 'observed' citations are not allowed - freeze the output/file with `kb.py freeze` and cite its id")
            continue
        if sid == "user":
            if not qs:
                problems.append(f"{where}: [src: user <date>] needs the owner's words as a quote (\"...\")")
                continue
            d = rest.strip().split()[0] if rest.strip() else ""
            files = user_files(d) if DATE.match(d) else []
            if not files:
                problems.append(f"{where}: [src: user {d}] - no owner messages saved for that date in sources/user/")
                continue
            for q in qs:
                if not any(wsnorm(q) in src_text(f) for f in files):
                    problems.append(f"{where}: owner quote not found in sources/user/{d}*: \"{q[:60]}\"")
            quotes += qs
            continue
        if sid not in srcs:
            problems.append(f"{where}: citation to unknown source '{sid}'")
            continue
        for q in qs:
            if wsnorm(q) not in src_text(srcs[sid]):
                problems.append(f"{where}: quote not found in {sid}: \"{q[:60]}\"")
        quotes += qs
    known = " ".join(src_text(srcs[m.group(1)]) for m in CIT.finditer(cites) if m.group(1) in srcs)
    known += " " + " ".join(wsnorm(q) for q in quotes)
    if not known.strip():
        return  # nothing citable resolved: the problems above already say why
    nums = numbers(claim, known)
    if nums:
        missing = num_missing(nums, numbers(known))
        if missing:
            problems.append(f"{where}: number(s) {', '.join(missing)} not in any cited source - cite the source that states them")
    bad = unsupported_dates(claim, [known])
    if bad:
        problems.append(f"{where}: date(s) {', '.join(bad)} not in any cited source (any notation counts) - cite the source that states them")


# ---------------- check ----------------
def check_note(p: Path, fm, body, srcs, ids, archived, red, problems, warnings):
    rel = p.relative_to(ROOT).as_posix()
    for k in REQUIRED:
        if not fm.get(k):
            problems.append(f"{rel}: missing frontmatter '{k}'")
    if fm.get("id") and fm["id"] != p.stem:
        problems.append(f"{rel}: id '{fm['id']}' != filename")
    if fm.get("type") and fm["type"] not in TYPES:
        problems.append(f"{rel}: unknown type '{fm['type']}'")
    for k in ("updated", "last_verified"):
        if fm.get(k) and not DATE.match(str(fm[k])):
            problems.append(f"{rel}: '{k}' not YYYY-MM-DD")
    if fm.get("status") and fm["status"] != "current":
        problems.append(f"{rel}: status '{fm['status']}' inside notes/ - use `kb.py archive` to retire a note")
    if "<claim," in body:
        problems.append(f"{rel}: template placeholder left in note")
    prev, fence = "", False
    for line in body.splitlines():
        s = line.strip()
        under = line[:1] in (" ", "\t") and bool(BULLET.match(prev) or prev[:1] in (" ", "\t"))
        if fence or (under and FENCE.match(line)):
            fence = not (fence and FENCE.match(line))
            prev = line if s else prev
            continue
        ok = not s or s.startswith(("#", "<!--", "History:")) or BULLET.match(line) or under or FOOT_DEF.match(line)
        if not ok:
            problems.append(f"{rel}: text outside a claim bullet is uncited: '{s[:60]}' - make it a cited bullet or remove it")
        prev = line if s else ""  # a blank line ends the bullet: no uncited paragraph can hang under it
    blocks = []
    cl = claims(body, blocks)
    for text, code in blocks:  # an example is exactly what ran: verbatim in a source its claim cites
        cited = [src_text(srcs[m.group(1)]) for m in CIT.finditer(text) if m.group(1) in srcs]
        cited += [src_text(f) for m in CIT.finditer(text) if m.group(1) == "user" and m.group(2).split()
                  for f in user_files(m.group(2).split()[0])]
        if not any(wsnorm(code) in x for x in cited):
            problems.append(f"{rel}: example under '{text[:50]}' is not verbatim in a source that claim cites - freeze "
                            "the query that ran (with its output) and paste it unchanged")
    used = set(FOOT_REF.findall("\n".join(l for l in body.splitlines() if not FOOT_DEF.match(l))))
    problems += [f"{rel}: footnote [^{m.group(1)}] is not used by any claim - remove it" for m in
                 map(FOOT_DEF.match, body.splitlines()) if m and m.group(1) not in used]
    for in_links, text in cl:
        if in_links:
            continue
        if "[src:" not in text:
            problems.append(f"{rel}: claim without [src:] '{text[:70]}' (link lists go under '## Related')")
            continue
        check_evidence(text, text, srcs, f"{rel}: '{text[:50]}'", problems)
    for m in LINK.finditer(body):
        t = red.get(m.group(1).strip(), m.group(1).strip())
        if t in ids or (HISTORY / f"{t}.md").exists():
            continue
        if t in archived:
            warnings.append(f"{rel}: links archived note [[{t}]] - remove or replace the link")
        else:
            problems.append(f"{rel}: broken link [[{m.group(1)}]]")


def check_inbox(p: Path, srcs, problems):
    rel = p.relative_to(ROOT).as_posix()
    text = p.read_text(encoding="utf-8")
    for item in re.split(r"(?m)^## ", text)[1:]:
        title = item.splitlines()[0].strip()
        claim = re.search(r"(?m)^claim:\s*(.+)$", item)
        ev = re.search(r"(?m)^evidence:\s*(.+)$", item)
        if not claim:
            continue
        if not ev or "[src:" not in ev.group(1):
            problems.append(f"{rel} '{title}': no evidence [src: ...]")
            continue
        check_evidence(claim.group(1), ev.group(1), srcs, f"{rel} '{title}'", problems)


def check_history(problems):
    for p in md_files(HISTORY):
        rel = p.relative_to(ROOT).as_posix()
        entries = re.split(r"(?m)^(?=## )", p.read_text(encoding="utf-8"))
        for e in entries:
            if not e.startswith("## "):
                continue
            if not HIST_HEAD.match(e):
                problems.append(f"{rel}: history heading must be '## Superseded YYYY-MM-DD': '{e.splitlines()[0][:60]}'")
            elif not re.search(r"(?mi)^reason:\s*\S", e):
                problems.append(f"{rel}: entry '{e.splitlines()[0]}' has no 'reason:' line")
            for line in e.splitlines():
                if BULLET.match(line) and "[src:" not in line:
                    problems.append(f"{rel}: superseded bullet without an inline [src: ...] (copy the old claim with its "
                                    f"citation written out, not a footnote marker): '{line.strip()[:60]}'")


def history_pool():
    parts = []
    for p in md_files(HISTORY):
        for e in re.split(r"(?m)^(?=## )", p.read_text(encoding="utf-8")):
            if HIST_HEAD.match(e) and re.search(r"(?mi)^reason:\s*\S", e):
                parts.append(norm(e))
    return " | ".join(parts)


def removed_claims_without_history():
    """Claims present at HEAD (full text) that are gone from notes/ and archive/ and not in a valid history entry."""
    head = head_texts("notes")
    if not head:
        return []
    current = set()
    for p in note_files() + md_files(ARCHIVE):
        current |= {norm(t) for _, t in claims(parse(p)[1])}
    pool, purged, out = history_pool(), purged_ids(), []
    for path, text in head.items():
        nid = Path(path).stem
        for in_links, t in claims(body_of(text)):
            n = norm(t)
            if in_links or len(n) < 12 or n in current or nid in purged:
                continue
            if n not in pool:
                out.append(f"{nid}: '{t[:70]}'")
    return out


def source_problems():
    """Frozen sources are never edited or deleted (the commit gate keeps such changes out of history), and new ones
    must come from kb.py freeze / fetch.py (their sha256 matches the body) - not be typed by an agent."""
    out, purged = [], purged_ids()
    new = {l[3:].strip().strip('"') for l in git("status", "--porcelain", "--untracked-files=all", "--", "sources/").splitlines()
           if l.startswith("??")} if (ROOT / ".git").exists() else {p.relative_to(ROOT).as_posix() for p in md_files(SOURCES)}
    for f in sorted(new):
        p = ROOT / f
        if not f.endswith(".md") or f.startswith("sources/user/") or not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        sha = str(parse(p)[0].get("sha256", ""))
        if not sha or hashlib.sha256(source_body(text).rstrip("\n").encode("utf-8")).hexdigest()[:16] != sha:
            out.append(f"{f}: new source was not frozen by `kb.py freeze` / `fetch.py` (sha256 missing or does not match "
                       "the body) - freeze the original file instead of writing the source by hand")
    for l in git("status", "--porcelain", "--", "sources/").splitlines():
        code, f = l[:2], l[3:].strip()
        if "M" in code:
            out.append(f"{f}: source edited after it was frozen (restore it with git; freeze a new source instead)")
        elif "D" in code and Path(f).stem not in purged:
            out.append(f"{f}: source deleted (only the forget flow may delete sources - see the fix skill)")
    return out


def removed_history_entries():
    """History is append-only: every '## Superseded' entry at HEAD must still exist (except purged notes)."""
    head = head_texts("history")
    if not head:
        return []
    cur = " | ".join(norm(p.read_text(encoding="utf-8")) for p in md_files(HISTORY))
    purged, out = purged_ids(), []
    for path, text in head.items():
        if Path(path).stem in purged:
            continue
        for e in re.split(r"(?m)^(?=## )", text):
            if HIST_HEAD.match(e) and norm(e) not in cur:
                out.append(f"{path}: history entry removed or changed: '{e.splitlines()[0]}' (history is append-only)")
    return out


def heartbeat_problem():
    """Under Claude Code the guard's pre-hook must have fired just now (this very command triggered it)."""
    if not os.environ.get("CLAUDECODE") or not (ROOT / "tools" / "hooks" / "guard.py").exists():
        return []
    hb = ((ROOT / ".git" / "kb-guard") if (ROOT / ".git").is_dir() else (ROOT / ".kb-guard")) / "heartbeat"
    if not hb.exists() or time.time() - hb.stat().st_mtime > 120:
        return ["guard heartbeat missing or stale: the hooks in .claude/settings.json are not running (uv on PATH? "
                "settings loaded?) - writes are unguarded until this is fixed"]
    return []


def guard_violations():
    """Fails while a file still holds the content a non-permitted role wrote; resolved entries are dropped."""
    sd = (ROOT / ".git" / "kb-guard") if (ROOT / ".git").is_dir() else (ROOT / ".kb-guard")
    f = sd / "violations.json"
    try:
        viol = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out, keep = [], {}
    purged = purged_ids()
    for r, v in viol.items():
        p = ROOT / r
        if not p.exists() and Path(r).stem in purged:
            continue  # the forget flow deleted it and the purge is recorded
        cur = hashlib.sha1(p.read_bytes()).hexdigest() if p.exists() else None
        if cur == v.get("bad_sha"):
            keep[r] = v
            out.append(f"{r}: changed by role '{v.get('role')}' ({v.get('tool', 'Bash')}), which may not write it. Restore it "
                       f"(`uv run tools/kb.py restore`); if the owner made this change, the owner runs "
                       "`uv run python tools/hooks/guard.py clear` in their own terminal")
    if keep != viol:
        f.write_text(json.dumps(keep, indent=1), encoding="utf-8")
    return out


GUARD_CASES = [  # (role, tool, input, expected exit)
    ("main", "Write", {"file_path": "notes/x.md"}, 0),
    ("main", "Write", {"file_path": "tools/new.py"}, 0),
    ("reviewer", "Write", {"file_path": "tools/kb.py"}, 2),
    ("main", "Write", {"file_path": "sources/user/2026-01-01-x.md"}, 2),
    ("reviewer", "Write", {"file_path": "meta/audits/x-review.md"}, 0),
    ("reviewer", "Write", {"file_path": "charter.md"}, 2),
    ("main", "Bash", {"command": "echo x > tools/hooks/guard.py"}, 2),
    ("main", "PowerShell", {"command": "Set-Content -Path charter.md -Value x"}, 2),
    ("main", "Bash", {"command": "uv run python work/q.py > work/out.csv"}, 0),
    ("main", "Bash", {"command": 'uv run tools/kb.py search "touch points"'}, 0),
]


def guard_selftest():
    """Runs the real guard code in-process (fast) plus one subprocess for the fail-closed path."""
    g = ROOT / "tools" / "hooks" / "guard.py"
    if not g.exists():
        return []
    import importlib.util, io, tempfile
    from contextlib import redirect_stderr
    spec = importlib.util.spec_from_file_location("kb_guard", g)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    out, old = [], os.environ.get("CLAUDE_PROJECT_DIR")
    try:
        os.environ["CLAUDE_PROJECT_DIR"] = str(ROOT)
        for role, tool, ti, want in GUARD_CASES:
            d = {"tool_name": tool, "tool_input": ti, "cwd": str(ROOT)}
            if role != "main":
                d["agent_type"] = role
            with redirect_stderr(io.StringIO()):
                got = guard.pre(d, heartbeat=False)
            if got != want:
                out.append(f"guard self-test: {role} {tool} {ti} should exit {want}")
        with tempfile.TemporaryDirectory() as t:  # post-command backstop
            os.environ["CLAUDE_PROJECT_DIR"] = t
            (Path(t) / "charter.md").write_text("x", encoding="utf-8")
            guard.write_manifest(Path(t).resolve())
            (Path(t) / "charter.md").write_text("changed by a script", encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                got = guard.post({"tool_name": "Bash", "tool_input": {"command": "uv run python work/x.py"}, "cwd": t})
            if got != 2 or not (Path(t) / ".kb-guard" / "violations.json").exists():
                out.append("guard self-test: a script changing an owner file must be recorded as a violation")
    finally:
        if old is None:
            os.environ.pop("CLAUDE_PROJECT_DIR", None)
        else:
            os.environ["CLAUDE_PROJECT_DIR"] = old
    r = subprocess.run([sys.executable, "-I", str(g), "pre"], input="not json", capture_output=True, text=True)
    if r.returncode != 2:
        out.append("guard self-test: malformed hook input must block (fail closed)")
    return out


def collect_problems(inbox=False):
    srcs, ids, red, problems, warnings = source_ids(), {}, redirects(), [], []
    problems += heartbeat_problem()
    for p in note_files():
        if p.stem in ids:
            problems.append(f"duplicate note id '{p.stem}': {ids[p.stem].relative_to(ROOT).as_posix()} and {p.relative_to(ROOT).as_posix()}")
        ids.setdefault(p.stem, p)
    archived = {p.stem for p in md_files(ARCHIVE)}
    for i in sorted(archived & set(ids)):
        problems.append(f"note id '{i}' exists in both notes/ and archive/")
    titles, aliases = {}, {}
    for p in note_files():
        fm, body = parse(p)
        check_note(p, fm, body, srcs, ids, archived, red, problems, warnings)
        n = len(CIT.sub(" ", body).split())
        if n > 400:
            warnings.append(f"{p.relative_to(ROOT).as_posix()}: {n} words (> 400) - split it if created in this filing, "
                            "otherwise propose a split (refactor skill)")
        t = str(fm.get("title", "")).lower().strip()
        if t:
            if t in titles:
                problems.append(f"duplicate title '{t}': {titles[t]} and {p.stem}")
            titles[t] = p.stem
        al = fm.get("aliases") or []
        for x in (al if isinstance(al, list) else [al]):
            aliases.setdefault(x.lower().strip(), set()).add(p.stem)
    for x, owners in aliases.items():
        clash = owners | ({titles[x]} if x in titles else set()) | ({x} if x in ids else set())
        if len(clash) > 1:
            warnings.append(f"alias '{x}' is shared by {sorted(clash)} - search becomes ambiguous")
    for p in md_files(SOURCES):
        fm, _ = parse(p)
        if not fm.get("id") and not fm.get("type"):
            problems.append(f"{p.relative_to(ROOT).as_posix()}: source without frontmatter")
    if inbox:
        for p in md_files(INBOX):
            if "processed" not in p.parts and p.parent.name != "tools":
                check_inbox(p, srcs, problems)
    check_history(problems)
    problems += source_problems()
    problems += [f"claim changed or removed since last commit without a history/ entry (supersede with "
                 f"'## Superseded <date>' + 'reason:'; wording-only edits use 'reason: rewording'): {k}"
                 for k in removed_claims_without_history()]
    problems += removed_history_entries()
    problems += guard_violations()
    if (ROOT / ".env").exists() and (ROOT / ".git").exists():
        if git("ls-files", ".env").strip():
            problems.append(".env is tracked by git - it may hold an API key: `git rm --cached .env`, rotate the key")
        elif subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode != 0:
            problems.append(".env is not git-ignored - add it to .gitignore before the next commit")
    if (ROOT / ".cache" / "embeddings.sqlite").exists():  # offline prune: forgotten/removed text leaves the cache
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import kbsem
            cfg = kbsem.config(ROOT)
            if cfg:
                kbsem.Store(ROOT, cfg).prune(u["key"] for u in sem_units(cfg))
        except (ImportError, sqlite3.Error) as ex:
            warnings.append(f"embedding cache not pruned: {ex}")
    return problems, warnings, ids


def cmd_check(a):
    problems, warnings, ids = collect_problems(a.inbox)
    for x in warnings:
        print("WARN", x)
    for x in problems:
        print("FAIL", x)
    print(f"{len(problems)} problem(s), {len(warnings)} warning(s) in {len(ids)} notes")
    sys.exit(1 if problems else 0)


# ---------------- verify / precheck ----------------
def changed_notes():
    out = set()
    for l in git("status", "--porcelain", "--untracked-files=all", "--", "notes/").splitlines():
        f = l[3:].strip().strip('"').split(" -> ")[-1]
        if f.endswith(".md"):
            out.add(Path(f).stem)
    return out


def context(text: str, q: str, width=250):
    t = " ".join(unicodedata.normalize("NFKC", text).translate(_WS_TABLE).split())
    i = t.casefold().find(wsnorm(q))
    if i < 0:
        return None
    return ("..." if i > width else "") + t[max(0, i - width):i + len(q) + width] + "..."


def evidence_flags(claim, quote, ctx, raw_source):
    """Cheap deterministic warnings for the reviewer (not failures)."""
    flags = []
    c = CIT.sub(" ", claim)
    evidence = (quote + " " + (ctx or "")).lower()
    dates = [d for d in re.findall(r"\d{4}-\d{2}-\d{2}", c) if d not in raw_source]
    if dates:
        flags.append(f"DATE NOT IN SOURCE: {', '.join(dates)}")
    qn = numbers(quote)
    if len(qn) > 1:  # several numbers in the quote: show what each claim number matched, so a label can't pass as a value
        shown = []
        for t, rd in numbers(c).items():
            hit = next((qt for qt, qr in qn.items() if qr & rd), None)
            if hit:
                m = re.search(r"(?:\S+\s+){0,3}" + re.escape(hit) + r"(?:\s+\S+){0,3}", quote)
                shown.append(f"{t} <- '{m.group(0) if m else hit}'")
        if shown:
            flags.append(f"NUMBER MATCHED IN: {'; '.join(shown)}")
    return flags


def cmd_verify(a):
    srcs, ids = source_ids(), note_ids()
    head_fm = head_texts("notes")
    def keyed(body):
        blocks = []
        cl = claims(body, blocks)
        code = dict(blocks)
        return [(l, t, code.get(t, ""), " ".join((t + code.get(t, "")).split())) for l, t in cl]
    head = {} if getattr(a, "all", False) else {Path(p).stem: {k for _, _, _, k in keyed(body_of(x))} for p, x in head_fm.items()}
    targets = a.ids or sorted(changed_notes())
    if not targets:
        print("no changed notes")
        return
    for nid in targets:
        if nid not in ids:
            print(f"## {nid}: not found")
            continue
        # full-bullet comparison: a changed citation or quote counts as a change
        cur = [(t, c) for l, t, c, k in keyed(parse(ids[nid])[1]) if not l and k not in head.get(nid, set())]
        new, examples = [t for t, _ in cur], dict(cur)
        print(f"## {nid} - {len(new)} new/changed claim(s)")
        fm_now = parse(ids[nid])[0]
        fm_old = next((parse_text(x)[0] for pth, x in head_fm.items() if Path(pth).stem == nid), {})
        for k in ("title", "summary", "aliases"):
            if str(fm_now.get(k, "")) != str(fm_old.get(k, "")):
                print(f"FRONTMATTER {k}: {fm_now.get(k, '')}  (search shows it on every hit: must agree with the cited claims)")
        for t in new:
            print(f"CLAIM: {t}")
            cited = {m.group(1) for m in CIT.finditer(t)}
            raw_cited = " ".join(srcs[s].read_text(encoding="utf-8") for s in cited if s in srcs)
            for s in sorted(cited - set(srcs) - {"user"}):
                print(f"  SOURCE MISSING: {s}")
            # newest sources on the subject first; the cited one is only where the claim came from
            print("  SOURCES ON THIS SUBJECT (newest first - read the newest before the cited one):")
            shown = set()
            for sid, d, sn in source_hits(t, srcs):
                shown.add(sid)
                print(f"    {d or 'undated'}  {sid}{'  (cited)' if sid in cited else ''}: {sn[:160]}")
            for s in sorted((cited & set(srcs)) - shown):
                print(f"    {src_date(s, srcs) or 'undated'}  {s}  (cited; not among the search hits)")
            dates = [x for x in re.findall(r"\d{4}-\d{2}-\d{2}", CIT.sub(" ", t))
                     if raw_cited and unsupported_dates(x, [wsnorm(raw_cited)])]
            if dates:
                print(f"  DATE NOT IN SOURCE: {', '.join(dates)} (not in any cited source, in any notation)")
            for m in CIT.finditer(t):
                sid, rest = m.group(1), m.group(2)
                if sid != "user":
                    continue  # owner messages: show the quoted words in context (the owner is the source)
                qs = QUOTE.findall(rest) or [None]
                files = user_files(rest.split()[0]) if rest.split() else []
                if not files:
                    print(f"  EVIDENCE user: NO OWNER MESSAGE FOR THAT DATE")
                for f in files:
                    raw = f.read_text(encoding="utf-8")
                    for q in qs:
                        ctx = context(raw, q) if q else None
                        if q and ctx is None:
                            continue
                        print(f"  EVIDENCE {f.relative_to(ROOT).as_posix()}{rest.split(chr(34))[0].rstrip()}: "
                              + (ctx if ctx else "(no quote - open the source at the locator and read it)"))
                        if q:
                            for fl in evidence_flags(t, q, ctx, raw):
                                print(f"  {fl}")
                            if sid == "user" and looks_pasted(source_body(raw)):
                                print("  OWNER QUOTE FROM A LONG/PASTED-LOOKING MESSAGE: is this the owner's own statement, "
                                      "or material they forwarded (freeze that as its own source with its real tier)?")
            if examples.get(t):
                print("  EXAMPLE (verbatim in a cited source; does it do what the claim says?):\n    "
                      + examples[t].strip().replace("\n", "\n    "))
            for line in similar_lines(t, own_note=nid):
                print(line)
            print()
    print("Reviewer: for each claim open the NEWEST source on its subject first and ask whether it still says this "
          "(numbers, units, entity, scope, conditions, decided vs planned); only then read the cited source. A citation "
          "shows where a claim came from, not that it is still true. Flags above are hints, not proof. Then check SIMILAR "
          "lines: a duplicate should have been merged; a different number/date is a conflict or a supersede; a SUPERSEDED "
          "match means an old value may be coming back.")


def source_hits(claim, srcs, k=6):
    """[(source id, date, snippet)] for the sources most about a claim's subject, newest first."""
    q = " ".join(re.findall(r"\w+", STAMP.sub(" ", LINK.sub(" ", CIT.sub(" ", claim)))))
    if not q.strip():
        return []
    hits, _, _ = keyword_search(q, k, scopes=("sources",))
    by_path = {p.relative_to(ROOT).as_posix(): sid for sid, p in srcs.items()}
    out = [(by_path[p], src_date(by_path[p], srcs), sn) for p, sn in hits if p in by_path]
    return sorted(out, key=lambda x: (x[1] is None, -(x[1].toordinal() if x[1] else 0)))


def precheck_state():
    """(digest, review_needed, changed_paths) for the uncommitted KB change. Pure move = every changed file's body
    at HEAD equals exactly one current file's body (per file, so moving a claim between notes needs review)."""
    dirs = ("notes", "history", "archive", "decisions")
    head = head_texts(*dirs)
    cur = {p.relative_to(ROOT).as_posix(): p.read_text(encoding="utf-8") for d in dirs for p in md_files(ROOT / d)}
    changed = sorted(p for p in set(head) | set(cur) if head.get(p) != cur.get(p))
    h = hashlib.sha1()
    for p in changed:
        h.update(f"{p}\0{cur.get(p, '<deleted>')}\0".encode("utf-8"))
    dig = h.hexdigest()[:16] if changed else "none"
    strip = lambda t: "\n".join(l for l in t.splitlines() if not l.startswith("updated:"))
    gone = sorted(strip(head[p]) for p in changed if p in head and p not in cur)
    came = sorted(strip(cur[p]) for p in changed if p in cur and p not in head)
    modified = [p for p in changed if p in head and p in cur]
    pure = bool(changed) and not modified and gone == came
    return dig, bool(changed) and not pure, changed


def cmd_precheck(a):
    dig, need, changed = precheck_state()
    print(f"digest: {dig}")
    if not changed:
        print("review: skip (no change to notes/history/archive/decisions)")
    elif not need:
        print("review: skip (pure moves - same files, new paths)")
    else:
        print("review: required\n" + "\n".join(f"  {p}" for p in changed))


def approved(dig):
    for f in md_files(META / "audits"):
        t = f.read_text(encoding="utf-8")
        if re.search(rf"(?mi)^digest:\s*{re.escape(dig)}\b", t) and re.search(r"(?mi)^\**verdict:?\**\s*approved", t):
            return f.relative_to(ROOT).as_posix()
    return None


def cmd_commit(a):
    """The only way agents commit: gate (check clean, no open forget, approved review of the current digest), then stage
    exactly the working tree that was reviewed - plus the owner messages its claims cite (git-ignored otherwise) - and
    commit. Uncited owner messages never reach git, so forgetting them leaves nothing in history."""
    cmd_commit_check(a)
    if not re.match(r"kb: \S", a.message):
        sys.exit("commit message must start with 'kb: '")
    subprocess.run(["git", "add", "-A"], cwd=ROOT, check=True)
    cited = sorted(cited_user_files())
    if cited:
        subprocess.run(["git", "add", "-f", "--", *cited], cwd=ROOT, check=True)
    r = subprocess.run(["git", "commit", "-q", "-m", a.message], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit((r.stdout + r.stderr).strip() or "git commit failed")
    print(git("log", "--oneline", "-1").strip())
    refresh_embeddings()


def cmd_commit_check(a):
    """Gate used by `kb.py commit`: check must be clean; with [review] mode = "always" the change must also be approved."""
    problems, _, _ = collect_problems(False)
    if problems:
        print("kb.py check has problems - fix them first:\n" + "\n".join(problems[:10]))
        sys.exit(1)
    if str(CFG.get("review", {}).get("mode", "audit")) != "always":
        print("ok")
        return
    dig, need, changed = precheck_state()
    if need and not approved(dig):
        print(f"the KB change (digest {dig}) has no approved review. Run the reviewer subagent; it writes "
              f"meta/audits/<timestamp>-review.md with 'Digest: {dig}' and 'Verdict: approved'.")
        sys.exit(1)
    print("ok")


# ---------------- freshness ----------------
_srcmeta = {}


def src_date(sid, srcs):
    if sid not in _srcmeta:
        fm = parse(srcs[sid])[0] if sid in srcs else {}
        d = next((str(fm[k]) for k in ("published", "date", "retrieved") if DATE.match(str(fm.get(k, "")))), None)
        lead = re.match(r"(\d{4}-\d{2}-\d{2})-", sid)
        if lead and (d is None or (str(fm.get("date")) == str(fm.get("retrieved")) and lead.group(1) < d)):
            d = lead.group(1)  # frozen before freeze kept the file-name date: the id carries the document's date
        _srcmeta[sid] = dt.date.fromisoformat(d) if d else None
    return _srcmeta[sid]


def claim_date(text, srcs, today=None):
    """When a claim was last known true: its 'as of' stamp, else the newest cited source date (future dates ignored).
    'since/from' stamps say when something started, not when it was verified."""
    today = today or dt.date.today()
    ds = [dt.date.fromisoformat(x) for x in FRESH.findall(text)]
    for c in CIT.finditer(text):
        sid, rest = c.group(1), c.group(2).split()
        if sid == "user" and rest and DATE.match(rest[0]):
            ds.append(dt.date.fromisoformat(rest[0]))
        elif sid != "user":
            d = src_date(sid, srcs)
            if d:
                ds.append(d)
    ds = [d for d in ds if d <= today]
    return max(ds) if ds else None


def stale_claims(p: Path, srcs, today):
    fm, body = parse(p)
    days = REVIEW_DAYS.get(fm.get("type", "topic"), DEFAULT_REVIEW)
    lv = str(fm.get("last_verified", ""))
    lv = dt.date.fromisoformat(lv) if DATE.match(lv) else None
    lv = lv if lv and lv <= today else None
    out = []
    for l, t in claims(body):
        if l:
            continue
        d = claim_date(t, srcs, today)
        if d and lv:
            d = max(d, lv)
        d = d or lv
        if not d:
            u = str(fm.get("updated", ""))
            d = dt.date.fromisoformat(u) if DATE.match(u) else None
        if d and d + dt.timedelta(days=days) <= today:
            out.append((d, t))
    return out


def cmd_stale(a):
    today = dt.date.fromisoformat(a.today) if a.today else dt.date.today()
    srcs, n = source_ids(), 0
    for p in note_files():
        s = stale_claims(p, srcs, today)
        if s:
            n += 1
            print(f"STALE {p.stem}: {len(s)} claim(s), oldest as of {min(d for d, _ in s)} - e.g. '{s[0][1][:70]}'")
    print(f"{n} note(s) with stale claims")


# ---------------- search ----------------
RRF_K = int(__import__("os").environ.get("KB_RRF_K", "5"))
MARGIN_DEFAULT = 0.6  # semantic-only hit: vector top-1 AND z(top1) - z(top2) >= margin (scale-free, benchmarked)
LAZY_LIMIT = 50
_engine = {}


def sem_text(title, text):
    t = CIT.sub(" ", text)
    t = LINK.sub(lambda m: m.group(1).replace("-", " "), t)
    t = " ".join(t.split())
    return f"{title}: {t}" if title else t


def sem_units(cfg):
    """Everything that gets embedded. Cards and claims of current notes; archive and history kept as separate kinds."""
    import kbsem
    units, titles = [], {}

    def add(kind, ref, path, text, raw, extra=""):
        units.append({"key": kbsem.Store.key(cfg, text), "kind": kind, "ref": ref, "path": path,
                      "text": text, "raw": raw, "extra": extra})
    for group, files in (("note", note_files()), ("archive", md_files(ARCHIVE))):
        for p in files:
            fm, body = parse(p)
            title = str(fm.get("title", p.stem))
            titles[p.stem] = title
            rel = p.relative_to(ROOT).as_posix()
            al = fm.get("aliases") or []
            al = al if isinstance(al, list) else [al]
            card = title + (". Also called: " + ", ".join(al) if al else "") + ". " + str(fm.get("summary", ""))
            add("card" if group == "note" else "archive", p.stem, rel, card, str(fm.get("summary", "")))
            for in_links, t in claims(body):
                if not in_links:
                    add("claim" if group == "note" else "archive", p.stem, rel, sem_text(title, t), t)
    for p in md_files(HISTORY):
        title = titles.get(p.stem, p.stem.replace("-", " "))
        for e in re.split(r"(?m)^(?=## )", p.read_text(encoding="utf-8")):
            if HIST_HEAD.match(e):
                d = e.split()[2]
                for in_links, t in claims(e):
                    if not in_links:
                        add("history", p.stem, p.relative_to(ROOT).as_posix(), sem_text(f"{title} (superseded {d})", t), t, d)
    for sc in [x for x in EMBED_SCOPES if x in SCOPES and x not in ("notes", "history")]:
        for p in scope_files([sc]):  # raw material: ~700-character chunks on paragraph boundaries
            title, _, _, body = doc_of(p)
            buf = ""
            paras = []
            for x in [x.strip() for x in re.split(r"\n\s*\n", body) if x.strip()]:
                for line in (x.splitlines() if len(x) > 700 else [x]):
                    paras += [line[i:i + 700] for i in range(0, len(line), 700)] or [line]
            for para in [x for x in paras if x.strip()] + [""]:
                if para and len(buf) + len(para) < 700:
                    buf = (buf + "\n" + para).strip()
                    continue
                if buf:
                    add(f"chunk:{sc}", p.stem, p.relative_to(ROOT).as_posix(), f"{title}: {' '.join(buf.split())}", buf)
                buf = para
    return units


def engine(lazy=True):
    """dict(cfg, store, units, vec, z) when semantic search is ready; dict(off=reason) or None when not configured."""
    if "e" in _engine:
        return _engine["e"]
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import kbsem
    except ImportError:
        _engine["e"] = None
        return None
    cfg = kbsem.config(ROOT)
    if not cfg:
        _engine["e"] = None
        return None
    try:
        store = kbsem.Store(ROOT, cfg)
        units = sem_units(cfg)
        done, missing = store.sync(units, limit=LAZY_LIMIT if lazy else None)
        if missing:
            e = {"off": f"index incomplete ({missing} units not embedded) - run `kb.py embed`"}
        else:
            vec = store.vectors(u["key"] for u in units)
            m = store.meta("margin:" + cfg["fingerprint"])
            e = {"cfg": cfg, "store": store, "units": units, "vec": vec, "kbsem": kbsem,
                 "margin": float(m) if m else MARGIN_DEFAULT, "calibrated": bool(m)}
    except kbsem.EmbedError as ex:
        e = {"off": str(ex)}
    except sqlite3.Error as ex:
        e = {"off": f"embedding cache busy/unreadable ({ex})"}
    _engine["e"] = e
    return e


TOKENIZERS = (("porter", "porter unicode61 remove_diacritics 2"),       # English stemming (one vote among three)
              ("prefix", "unicode61 remove_diacritics 2"),              # any language: word prefixes stand in for stems
              ("trigram", "trigram remove_diacritics 1"),               # any language: compounds, inflections, substrings
              ("trigram", "trigram"))                                    # older SQLite without remove_diacritics


def _fts_tables(con, rows):
    made, kinds = [], set()
    for kind, tok in TOKENIZERS:
        if kind in kinds:
            continue
        name = f"d_{kind}"
        try:
            con.execute(f"CREATE VIRTUAL TABLE {name} USING fts5(path, title, aliases, summary, body, tokenize='{tok}')")
        except sqlite3.OperationalError:
            continue  # tokenizer not in this SQLite build
        con.executemany(f"INSERT INTO {name} VALUES (?,?,?,?,?)", rows)
        made.append((kind, name))
        kinds.add(kind)
    return made


def _match_terms(kind, terms):
    if kind == "trigram":
        return [t for t in terms if len(t) >= 3]
    if kind == "prefix":  # cut a short ending: 'contracts' -> 'contrac*', 'bewaartermijnen' -> 'bewaartermij*'
        return [(t[:-2] if len(t) >= 7 else t[:-1] if len(t) >= 5 else t) + "*" if len(t) >= 5 else t for t in terms]
    return terms


def _q(t):
    return f'"{t[:-1]}"*' if t.endswith("*") else f'"{t}"'


SCOPES = {"notes": ("notes",), "history": ("history", "archive"), "sources": ("sources",), "reports": ("reports",),
          "inbox": ("inbox",), "work": ("work",), "meta": ("meta",), "data": ("data",)}
TEXT_EXT = {".md", ".txt", ".csv", ".tsv", ".json", ".html", ".htm", ".xml", ".yaml", ".yml", ".log"}  # not code


def scope_files(scopes):
    """Text files in the chosen scopes (never tools/, .claude/ or code files; never owner messages no claim cites)."""
    out = []
    cited = None
    for sc in scopes:
        for d in SCOPES[sc]:
            base = ROOT / d
            if base.is_dir():
                found = sorted(p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_EXT
                               and not any(x.startswith(".") for x in p.relative_to(ROOT).parts))
                if d == "sources":
                    cited = cited_user_files() if cited is None else cited
                    found = [p for p in found if p.parent.name != "user" or p.relative_to(ROOT).as_posix() in cited]
                out += found
    return out


def doc_of(p: Path):
    """(title, summary, aliases, body) of any text file; markdown frontmatter when present."""
    try:
        text = p.read_text(encoding="utf-8", errors="replace")[:400_000]
    except OSError:
        return p.stem, "", [], ""
    fm, body = parse_text(text) if p.suffix.lower() == ".md" else ({}, text)
    al = fm.get("aliases", "")
    al = al if isinstance(al, list) else [str(al)] if al else []
    return str(fm.get("title", p.stem)), str(fm.get("summary", "")), al, body


_KW_INDEX = {}


def keyword_search(query, k, scopes=("notes",)):
    """Language-free keyword search: three FTS5 rankings (porter, prefix, trigram) fused by rank. No stopword list:
    query words found in most documents are dropped by their document frequency. The index is built once per process
    and scope set (verify searches once per claim)."""
    key = tuple(scopes)
    if key not in _KW_INDEX:
        con = sqlite3.connect(":memory:")
        meta, rows = {}, []
        for p in scope_files(scopes):
            title, summ, al, body = doc_of(p)
            r = p.relative_to(ROOT).as_posix()
            meta[r] = (title, summ, [x.lower() for x in al], p)
            rows.append((r, title, " ".join(al), summ, body))
        _KW_INDEX[key] = (con, meta, rows, _fts_tables(con, rows) if rows else [])
    con, meta, rows, tables = _KW_INDEX[key]
    if not rows:
        return [], set(), meta
    words = [t for t in re.findall(r"\w+", query.casefold()) if t]
    if not words:
        sys.exit("empty query")
    n = len(rows)
    base = next((name for kind, name in tables if kind == "prefix"), tables[0][1])
    df = {}
    for t in set(words):
        try:
            df[t] = con.execute(f"SELECT count(*) FROM {base} WHERE {base} MATCH ?", (_q(t),)).fetchone()[0]
        except sqlite3.OperationalError:
            df[t] = 0
    terms = [t for t in words if not (n >= 8 and df[t] > n * 0.3)] or words
    fused, snip = {}, {}
    for kind, name in tables:
        mt = _match_terms(kind, terms)
        if not mt:
            continue
        sql = (f"SELECT path, snippet({name}, 4, '[', ']', ' ... ', 12), bm25({name}, 0, 8.0, 6.0, 3.0, 1.0) AS r "
               f"FROM {name} WHERE {name} MATCH ? ORDER BY r LIMIT ?")
        try:
            got = con.execute(sql, (" AND ".join(_q(t) for t in mt), k * 3)).fetchall()
            if len(got) < k and len(mt) > 1:
                seen = {g[0] for g in got}
                got += [g for g in con.execute(sql, (" OR ".join(_q(t) for t in mt), k * 3)).fetchall() if g[0] not in seen]
        except sqlite3.OperationalError:
            continue
        for rank, (path, sn, _) in enumerate(got):
            fused[path] = fused.get(path, 0) + 1 / (2 + rank)  # K=2 and df 0.3 tuned on experiments/semantic
            snip.setdefault(path, sn)
    short = [t for t in terms if len(t) < 3]
    if short and not fused:  # only very short words ("EU", "Q3"): plain substring scan
        for r in rows:
            text = " ".join(r[1:]).casefold()
            hits = sum(bool(re.search(rf"\b{re.escape(t)}\b", text)) for t in short)
            if hits:
                fused[r[0]] = hits
                snip[r[0]] = r[1]
    q = " ".join(words)
    exact = {p for p in fused if meta[p][0].lower() == q or any(x and re.search(rf"\b{re.escape(x)}\b", q) for x in meta[p][2])}
    ranked = sorted(fused, key=lambda p: (p not in exact, -fused[p]))[:k]
    return [(p, " ".join(snip[p].split())) for p in ranked], exact, meta


def vector_rank(e, text, kinds, query=True):
    """[(path, best_score, best_z, best_unit)] sorted by score - one entry per file."""
    qv = e["kbsem"].embed(e["cfg"], [text], query=query)[0]
    us = [u for u in e["units"] if u["kind"] in kinds and u["key"] in e["vec"]]
    scores = [e["kbsem"].dot(qv, e["vec"][u["key"]]) for u in us]
    zs = e["kbsem"].zscores(scores)
    best = {}
    for u, s, z in zip(us, scores, zs):
        if u["path"] not in best or s > best[u["path"]][0]:
            best[u["path"]] = (s, z, u)
    return sorted(((p, s, z, u) for p, (s, z, u) in best.items()), key=lambda x: -x[1])


def reranker():
    """Reranker config (+ calibrated threshold) or None."""
    if "r" not in _engine:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            import kbsem
            cfg = kbsem.rerank_config(ROOT)
        except ImportError:
            cfg = None
        if cfg:
            try:
                cfg["threshold"] = json.loads((ROOT / ".cache" / "rerank.json").read_text(encoding="utf-8")).get(cfg["fingerprint"])
            except (OSError, ValueError):
                cfg["threshold"] = None
        _engine["r"] = cfg
    return _engine["r"]


def note_doc(p, meta, u):
    """What the reranker reads for one hit: title, summary and the best-matching claim (or the first claims)."""
    title, summ, _, path = meta.get(p, (Path(p).stem, "", [], ROOT / p))
    if u is not None and u["kind"] != "card":
        body = sem_text("", u["raw"])
    else:
        body = " ".join(sem_text("", t) for l, t in claims(parse(path)[1])[:3] if not l) if Path(path).exists() else ""
    return f"{title}. {summ}\n{body}"[:800]


def run_search(query, k=8, scopes=("notes",), keyword=False, log=True, rerank=True):
    rr = None if (keyword or not rerank) else reranker()
    kw, exact, meta = keyword_search(query, max(k, 20) if rr else k, scopes)
    res = {"mode": None, "rows": [], "sem": [], "rr": []}
    e = None if keyword else engine()
    note, vr = [], []
    if e is not None and "off" not in e:
        kinds = ({"card", "claim"} if "notes" in scopes else set()) | ({"history", "archive"} if "history" in scopes else set())
        kinds |= {f"chunk:{sc}" for sc in scopes if sc in EMBED_SCOPES}
        uncovered = [sc for sc in scopes if sc not in EMBED_SCOPES]
        if uncovered:
            note.append(f"semantic does not cover {', '.join(uncovered)} (kb.toml [search] embed) - keyword only there")
        try:
            vr = vector_rank(e, query, kinds)
        except e["kbsem"].EmbedError as ex:
            e = {"off": str(ex)}
    if e is not None and "off" in e:
        note.append(f"semantic unavailable: {e['off']}")
    kwrank = {p: i for i, (p, _) in enumerate(kw)}
    vrank = {p: i for i, (p, *_rest) in enumerate(vr)}
    vbest = {p: (z, u) for p, s, z, u in vr}
    gated = set()
    if vr:
        res["sem"] = [(p, z) for p, s, z, u in vr[:10]]
        lead = vr[0][2] - vr[1][2] if len(vr) > 1 else 0
        gated = {vr[0][0]} if lead >= e["margin"] else set()
        mode = f"hybrid (semantic-only hits need a clear lead: margin {e['margin']:.2f}, {'calibrated' if e['calibrated'] else 'default'})"
    else:
        mode = "keyword"
    cand = list(kwrank) + [x[0] for x in vr[:3] if x[0] in gated and x[0] not in kwrank]
    fused = lambda p: (1 / (RRF_K + kwrank[p] + 1) if p in kwrank else 0) + (1 / (RRF_K + vrank[p] + 1) if p in vrank else 0)
    cand.sort(key=lambda p: (p not in exact, -fused(p)))
    if rr:
        import kbsem
        pool = list(dict.fromkeys(cand + [x[0] for x in vr[:20]]))[:30]
        try:
            sc = dict(zip(pool, kbsem.rerank(rr, query, [note_doc(p, meta, vbest.get(p, (None, None))[1]) for p in pool])))
            res["rr"] = [(p, sc[p], p in kwrank) for p in pool]
            thr = rr["threshold"]
            # keyword hits always stay eligible (keyword is the source of truth); meaning-only hits need the lead
            # rule, or - once calibrated - a reranker score above the calibrated threshold
            cand = [p for p in pool if p in kwrank or p in gated or (thr is not None and sc[p] >= thr)]
            cand.sort(key=lambda p: (p not in exact, -sc[p]))
            mode += f" + rerank ({'threshold %.3f, calibrated' % thr if thr is not None else 'uncalibrated: reorders only'})"
        except kbsem.EmbedError as ex:
            note.append(f"rerank unavailable: {ex}")
    elif keyword and (engine() is not None or reranker() is not None):
        note.append("--keyword")
    if vr or rr or note:
        res["mode"] = mode + (f" ({'; '.join(note)})" if note else "")
    snips = dict(kw)
    for p in cand[:k]:
        z, u = vbest.get(p, (None, None))
        match = "both" if p in kwrank and vrank.get(p, 99) < 3 else ("keyword" if p in kwrank else "semantic")
        snip = snips.get(p, "") if match == "keyword" else (u["raw"] if u else snips.get(p, ""))
        res["rows"].append((p, snip, match))
        if match == "semantic" and log:
            log_miss(f"{dt.date.today()}\tALIAS-GAP {query} -> {Path(p).stem}\n")
    return res, meta


def open_items():
    """[[note-id]] -> open lines from open-questions/parking. Lines starting with RESOLVED are closed."""
    out = {}
    for f in ("open-questions.md", "parking.md"):
        p = META / f
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if re.match(r"\s*[-*]?\s*(RESOLVED|~~)", line, re.I):
                    continue
                for m in LINK.finditer(line):
                    out.setdefault(m.group(1).strip(), []).append(f"{f.split('.')[0].upper()}: {line.strip()[:140]}")
    return out


def log_miss(line):
    MISSES.parent.mkdir(exist_ok=True)
    with MISSES.open("a", encoding="utf-8") as f:
        f.write(line)


def cmd_search(a):
    scopes = list(SCOPES) if a.all else [x.strip() for x in (a.scope or "notes").split(",") if x.strip()]
    scopes = (["sources"] if a.sources else scopes) + (["history"] if a.history and "history" not in scopes else [])
    bad = [x for x in scopes if x not in SCOPES]
    if bad:
        sys.exit(f"unknown scope {bad}; use {', '.join(SCOPES)} or --all")
    a.sources = scopes != ["notes"] and "notes" not in scopes  # misses are logged for note searches only
    res, meta = run_search(a.query, a.k, scopes, a.keyword)
    if res["mode"]:
        print(f"mode: {res['mode']}")
    if not res["rows"]:
        print("no results")
        if not a.sources:
            log_miss(f"{dt.date.today()}\t{a.query}\n")
        return
    srcs, today, opens = source_ids(), dt.date.today(), open_items()
    cited_by = {}
    if any(not p.startswith("notes/") for p, _, _ in res["rows"]):
        for p in note_files():
            for m in CIT.finditer("\n".join(t for _, t in claims(parse(p)[1]))):
                cited_by.setdefault(m.group(1), []).append(f"notes/{p.stem}")
    for path, snip, match in res["rows"]:
        title, summ, _, p = meta.get(path, (Path(path).stem, "", [], ROOT / path))
        tag = "" if res["mode"] is None else f" | match: {match}"
        citers = cited_by.get(Path(path).stem, []) if path.startswith("sources/") else []
        kind = ("" if path.startswith("notes/") else " | BLOCKED - disputed, not knowledge" if "-blocked-" in path
                else " | SUPERSEDED / ARCHIVED - not current" if path.startswith(("history/", "archive/"))
                else f" | SOURCE cited by {', '.join(citers[:3])} - answer from it, citing note and source" if citers
                else " | RAW - not reviewed, label it as such in an answer")
        print(f"{path} | {title} | {summ}{tag}{kind}\n    {snip}")
        if path.startswith("notes/"):
            s = stale_claims(p, srcs, today)
            if s:
                print(f"    STALE: {len(s)} claim(s) as of {min(d for d, _ in s)} or older - say 'as of <date>, may be outdated'")
            for o in opens.get(p.stem, []):
                print(f"    OPEN {o}")


def find_similar(text, k=3, skip_ref=None):
    """Existing claims (current + superseded) that may state the same fact: keyword overlap and, if configured, vectors."""
    words = lambda s: {w for w in re.findall(r"\w+", sem_text("", s).lower()) if w not in STOP and len(w) > 1}
    tw = words(text)
    cand = {}
    pool = []
    for p in note_files():
        title = str(parse(p)[0].get("title", p.stem))
        pool += [("claim", p.stem, t, "") for l, t in claims(parse(p)[1]) if not l]
    for p in md_files(HISTORY):
        for e in re.split(r"(?m)^(?=## )", p.read_text(encoding="utf-8")):
            if HIST_HEAD.match(e):
                pool += [("history", p.stem, t, e.split()[2]) for l, t in claims(e) if not l]
    nt = norm(text)
    for kind, ref, raw, d in pool:
        if kind != "history" and norm(raw) == nt:
            continue
        shared = len(tw & words(raw))
        if tw and shared >= max(2, 0.5 * len(tw)):
            cand[(kind, ref, raw)] = (shared / len(tw), d)
    e = engine()
    if e is not None and "off" not in e:
        try:
            qv = e["kbsem"].embed(e["cfg"], [sem_text("", text)], query=False)[0]
            us = [u for u in e["units"] if u["kind"] in ("claim", "history") and u["key"] in e["vec"]]
            scores = [e["kbsem"].dot(qv, e["vec"][u["key"]]) for u in us]
            ranked = [x for x in sorted(zip(us, scores, e["kbsem"].zscores(scores)), key=lambda x: -x[1]) if norm(x[0]["raw"]) != nt]
            # a missed duplicate/conflict is silent corruption, a false neighbour is a labelled line: show the top 2
            for u, s, z in ranked[:2]:
                key = (u["kind"], u["ref"], u["raw"])
                cand[key] = (max(1.0 + s, cand.get(key, (0,))[0]), u["extra"])
        except e["kbsem"].EmbedError:
            pass
    out = sorted(cand.items(), key=lambda x: -x[1][0])[:k + 2]
    return [(kind, ref, raw, d) for (kind, ref, raw), (sc, d) in out]


def similar_lines(text, own_note=None):
    lines = []
    for kind, ref, raw, d in find_similar(text):
        label = f"SUPERSEDED {d} in history/{ref}" if kind == "history" else ("same note" if ref == own_note else f"note {ref}")
        a, b = numbers(text), numbers(raw)
        da, db = num_missing(a, b), num_missing(b, a)
        diff = f"  [NUMBERS/DATES DIFFER: {', '.join(da) or '-'} vs {', '.join(db) or '-'}]" if a and b and (da or db) else ""
        lines.append(f"  SIMILAR ({label}): {raw}{diff}")
    return lines


def cmd_similar(a):
    lines = similar_lines(a.text)
    e = engine()
    print(f"mode: {'keyword overlap + vectors' if e and 'off' not in e else 'keyword overlap only'}")
    print("\n".join(lines) if lines else "none")
    print("Similar is not the same: merge only if entity, scope, numbers and dates all match. "
          "Different number/date = supersede (clearly newer evidence) or conflict (open-questions), never merge.")


def cmd_embed(a):
    e = engine(lazy=False)
    if e is None:
        sys.exit("semantic search not configured (KB_EMBED_URL / KB_EMBED_MODEL) - keyword search only")
    if "off" in e:
        sys.exit(f"semantic search unavailable: {e['off']}")
    for w in e["kbsem"].warnings(e["cfg"]):
        print("WARN", w)
    if not e["store"].canary_ok():
        print("WARN provider returned different vectors for the canary text - model changed: re-embedding everything")
        e["store"].db.execute("DELETE FROM vec")
        e["store"].db.commit()
        _engine.clear()
        e = engine(lazy=False)
    pruned = e["store"].prune(u["key"] for u in e["units"])
    kinds = Counter(u["kind"] for u in e["units"])
    print(f"embeddings ready: {len(e['units'])} units ({dict(kinds)}), pruned {pruned} stale; model {e['cfg']['KB_EMBED_MODEL']}; "
          f"semantic margin {e['margin']:.2f} ({'calibrated' if e['calibrated'] else 'default - calibrate with search-eval --calibrate'})")


def cmd_search_eval(a):
    rows = []
    lines = Path(a.file).read_text(encoding="utf-8").splitlines()
    golden = any(re.match(r"\s*Q\d+\s*\|", l) for l in lines)
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "|" not in line:
            continue
        if golden and not re.match(r"\s*Q\d+\s*\|", line):
            continue
        f = [x.strip() for x in line.split("|")]
        if re.match(r"Q\d+$", f[0]):  # eval/golden.md: Q01 | question | answer | category | notes: id,id
            n = next((x for x in f if x.startswith("notes:")), None)
            if n is None:
                continue
            rows.append((f[1], [i.strip() for i in n[6:].split(",") if i.strip()], f[3] if len(f) > 3 else "golden"))
        else:  # query | id,id | kind
            rows.append((f[0], [i.strip() for i in f[1].split(",") if i.strip()], f[2] if len(f) > 2 else "q"))
    e = engine(lazy=False)
    rr = reranker()
    modes = ["keyword"] + (["hybrid"] if e and "off" not in e else []) + (["rerank"] if rr else [])
    res = {m: {} for m in modes}
    for m in modes:
        for q, exp, kind in rows:
            r, _ = run_search(q, k=5, keyword=(m == "keyword"), rerank=(m == "rerank"), log=False)
            ids = [Path(p).stem for p, _, _ in r["rows"]]
            semonly = [Path(p).stem for p, _, mt in r["rows"] if mt == "semantic"]
            res[m][q] = (ids, semonly, r["sem"], r["rr"])
    print(f"{len(rows)} queries; modes: {', '.join(modes)}")
    for kind in sorted({k for _, _, k in rows}):
        qs = [(q, exp) for q, exp, kd in rows if kd == kind]
        for m in modes:
            if all(not exp for _, exp in qs):
                fp = sum(bool(res[m][q][1]) for q, _ in qs)
                print(f"{kind:14} {m:8} n={len(qs):3}  no expected note: semantic-only hits on {fp}/{len(qs)}")
                continue
            r1 = sum(bool(set(res[m][q][0][:1]) & set(exp)) for q, exp in qs if exp)
            r5 = sum(bool(set(res[m][q][0][:5]) & set(exp)) for q, exp in qs if exp)
            mrr = sum(next((1 / (i + 1) for i, x in enumerate(res[m][q][0]) if x in exp), 0) for q, exp in qs if exp)
            n = sum(1 for _, exp in qs if exp)
            print(f"{kind:14} {m:8} n={n:3}  R@1 {r1 / n:.2f}  R@5 {r5 / n:.2f}  MRR {mrr / n:.2f}")
    for m in modes[1:]:
        win = sum(1 for q, exp, _ in rows if exp and bool(set(res[m][q][0]) & set(exp)) and not set(res['keyword'][q][0]) & set(exp))
        loss = sum(1 for q, exp, _ in rows if exp and bool(set(res['keyword'][q][0]) & set(exp)) and not set(res[m][q][0]) & set(exp))
        print(f"paired R@5 vs keyword: {m} wins {win}, keyword wins {loss}")
    if a.calibrate and "rerank" in modes and "hybrid" not in modes:
        print("rerank threshold not calibrated: without embeddings the reranker only reorders keyword hits")
    if a.calibrate and "rerank" in modes and "hybrid" in modes:
        neg = [q for q, exp, _ in rows if not exp]
        pos = [(q, exp) for q, exp, _ in rows if exp]
        best = None
        print("rerank calibration (meaning-only hit = not found by keyword, reranker score >= threshold):")
        for t in [x / 20 for x in range(1, 20)]:
            fp = sum(any(s >= t and not inkw for p, s, inkw in res["rerank"][q][3]) for q in neg)
            tp = sum(any(s >= t and not inkw and Path(p).stem in exp for p, s, inkw in res["rerank"][q][3]) for q, exp in pos)
            print(f"  threshold {t:.2f}: no-answer queries with a meaning-only hit {fp}/{len(neg)}, answers rescued {tp}/{len(pos)}")
            if best is None and len(neg) >= 40 and fp / len(neg) <= 0.05:
                best = t
        if best is not None:
            f = ROOT / ".cache" / "rerank.json"
            f.parent.mkdir(exist_ok=True)
            d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
            d[rr["fingerprint"]] = best
            f.write_text(json.dumps(d), encoding="utf-8")
            print(f"stored rerank threshold {best:.2f} for this reranker")
        else:
            print("rerank threshold not stored: need >= 40 no-answer queries and a threshold with <= 5% meaning-only hits on them")
    if a.calibrate and "hybrid" in modes:
        neg = [q for q, exp, _ in rows if not exp]
        pos = [(q, exp) for q, exp, _ in rows if exp]
        lead = lambda q: res["hybrid"][q][2][0][1] - res["hybrid"][q][2][1][1] if len(res["hybrid"][q][2]) > 1 else 0
        top = lambda q: Path(res["hybrid"][q][2][0][0]).stem if res["hybrid"][q][2] else None
        best = None
        print("calibration (semantic-only hit = vector top-1 with a lead >= margin, not already found by keyword):")
        for m in [x / 10 for x in range(1, 16)]:
            fp = sum(lead(q) >= m and top(q) not in res["keyword"][q][0] for q in neg)
            tp = sum(lead(q) >= m and top(q) in exp and top(q) not in res["keyword"][q][0] for q, exp in pos)
            print(f"  margin {m:.1f}: no-answer queries with a semantic-only hit {fp}/{len(neg)}, answers rescued {tp}/{len(pos)}")
            if best is None and len(neg) >= 40 and fp / len(neg) <= 0.05:
                best = m
        if best is not None:
            e["store"].meta("margin:" + e["cfg"]["fingerprint"], str(best))
            print(f"stored margin {best:.1f} for this model/prefix (<= 5% semantic-only hits on the {len(neg)} no-answer queries)")
        else:
            print("not stored: need >= 40 no-answer queries and a margin with <= 5% semantic-only hits on them")


# ---------------- maintenance ----------------
def cmd_new(a):
    if a.type not in TYPES:
        sys.exit(f"unknown type {a.type}; use one of {sorted(TYPES)}")
    taken = {p.stem: p for d in (NOTES, ARCHIVE) for p in md_files(d)}
    if a.id in taken:
        sys.exit(f"{taken[a.id].relative_to(ROOT).as_posix()} exists - extend it (or pick another id)")
    p = NOTES / f"{a.id}.md"
    today = a.today or dt.date.today().isoformat()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"""---
id: {a.id}
type: {a.type}
title: {a.title}
summary: {a.summary}
aliases: []
status: current
updated: {today}
---
## Claims
- <claim, stand-alone, with date if it can change> [src: <source-id> <locator> "exact quote"]
""", encoding="utf-8")
    print(f"created {p.relative_to(ROOT).as_posix()}")


def refresh_embeddings():
    """Bring the optional embedding index up to date (run after each commit; never fails the caller)."""
    try:
        e = engine(lazy=False)
    except Exception as ex:  # never fail index because of the embedding provider
        e = {"off": str(ex)}
    if e is not None:
        if "off" in e:
            print(f"WARN embeddings not updated: {e['off']} (search falls back to keyword)")
        else:
            try:
                if not e["store"].canary_ok():  # provider changed the model behind the same name
                    print("WARN embedding model changed (canary differs): re-embedding everything")
                    e["store"].db.execute("DELETE FROM vec")
                    e["store"].db.commit()
                    _engine.clear()
                    e = engine(lazy=False)
            except Exception as ex:
                print(f"WARN canary check failed: {ex}")
            if e and "off" not in e:
                pruned = e["store"].prune(u["key"] for u in e["units"])
                print(f"embeddings: {len(e['units'])} units up to date (pruned {pruned})")


def cmd_links(a):
    ids, target = note_ids(), a.id
    if target not in ids:
        sys.exit(f"no note {target}")
    _, body = parse(ids[target])
    print("outlinks:", sorted({m.group(1).strip() for m in LINK.finditer(body)}) or "none")
    back = [i for i, p in ids.items() if i != target and re.search(r"\[\[" + re.escape(target) + r"[\]#|]", p.read_text(encoding="utf-8"))]
    print("backlinks:", back or "none")


def cmd_mv(a):
    ids = note_ids()
    if a.id not in ids:
        sys.exit(f"no note {a.id}")
    dest = NOTES / a.folder / f"{a.id}.md"
    if dest.exists():
        sys.exit(f"{dest} exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    ids[a.id].rename(dest)
    print(f"moved {a.id} -> {dest.relative_to(ROOT).as_posix()} (id unchanged, links still resolve)")


def cmd_archive(a):
    ids = note_ids()
    if a.id not in ids:
        sys.exit(f"no note {a.id}")
    today = dt.date.today().isoformat()
    src = ids[a.id]
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^status:.*$", f"status: archived\narchived: {today}\narchived_reason: {a.reason}", text, count=1)
    ARCHIVE.mkdir(exist_ok=True)
    dest = ARCHIVE / f"{a.id}.md"
    dest.write_text(text, encoding="utf-8")
    src.unlink()
    back = [i for i, p in note_ids().items() if re.search(r"\[\[" + re.escape(a.id) + r"[\]#|]", p.read_text(encoding="utf-8"))]
    print(f"archived {a.id} -> archive/{a.id}.md" + (f"; notes still linking it: {back}" if back else ""))


def cmd_freeze(a):
    """Byte-exact copy of a local file into sources/<kind>/ with frontmatter + hash - no model retyping."""
    src = Path(a.path)
    if not src.is_file():
        sys.exit(f"no file {src}")
    if src.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            sys.exit("PDF needs pypdf: uv run --with pypdf tools/kb.py freeze <file.pdf> ...")
        text = "".join(f"<!-- page {i} -->\n{pg.extract_text() or ''}\n" for i, pg in enumerate(PdfReader(str(src)).pages, 1))
    else:
        raw = src.read_bytes()
        enc = "utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig"  # PowerShell 5.1 '>' writes UTF-16
        text = raw.decode(enc, "replace").replace("\r\n", "\n")
        if src.resolve().parent == (SOURCES / "user").resolve():  # material the owner pasted: freeze the message body
            text = source_body(text).strip() + "\n"
    today = dt.date.today().isoformat()
    stem = src.stem
    named = re.match(r"(\d{4}-\d{2}-\d{2})[-_ ]+(.+)", stem)  # 2026-09-14-ops-sync.txt -> date 2026-09-14, slug ops-sync
    if named and not a.slug:
        stem = named.group(2)
    slug = re.sub(r"[^a-z0-9-]+", "-", (a.slug or stem).lower()).strip("-")[:50]
    sdate = a.date or (named.group(1) if named else today)  # the document's own date, not the day it was frozen
    sid = f"{sdate}-{slug}"
    out = SOURCES / a.kind / f"{sid}.md"
    if out.exists():
        sys.exit(f"{out.relative_to(ROOT).as_posix()} exists - cite it or choose another --slug")
    out.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256(text.rstrip("\n").encode("utf-8")).hexdigest()[:16]
    title = (a.title or src.stem).replace('"', "'")
    out.write_text(f"---\nid: {sid}\ntype: {a.kind}\ntitle: \"{title}\"\norigin: {a.origin or src.as_posix()}\n"
                   f"date: {sdate}\nretrieved: {today}\nsha256: {sha}\ntier: {a.tier}\n---\n{text}",
                   encoding="utf-8", newline="\n")
    print(f"froze {out.relative_to(ROOT).as_posix()} - cite as [src: {sid} <locator> \"exact quote\"]")


def cmd_restore(a):
    """Undo exactly the changes the guard recorded as violations: back to the committed content, or delete if new.
    Touches nothing else - other uncommitted work is kept."""
    sd = (ROOT / ".git" / "kb-guard") if (ROOT / ".git").is_dir() else (ROOT / ".kb-guard")
    try:
        viol = json.loads((sd / "violations.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        viol = {}
    if not viol:
        print("nothing to restore: no guard violations recorded")
        return
    for r, v in sorted(viol.items()):
        p = ROOT / r
        cur = hashlib.sha1(p.read_bytes()).hexdigest() if p.exists() else None
        if cur != v.get("bad_sha"):
            print(f"skip {r}: changed again since the violation (resolve by hand)")
            continue
        blob = subprocess.run(["git", "show", f"HEAD:{r}"], cwd=ROOT, capture_output=True) if has_head() else None
        if blob is not None and blob.returncode == 0:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(blob.stdout)
            print(f"restored {r}")
        elif v.get("existed"):
            print(f"skip {r}: not in the last commit but existed before the violation - remove the added lines by hand")
            continue
        elif p.exists():
            p.unlink()
            print(f"deleted {r} (created by the violation)")
    guard_violations()  # drops the resolved entries
    print("done - now make the intended change properly (cited, with history)")


def cmd_forget(a):
    """Forget flow: record the purge FIRST, then delete the named sources / processed candidates.
    Note ids are only recorded - remove their claims with Edit (no history entry)."""
    # the reason is a fixed code: free text would carry the forgotten content into a committed file
    srcs, today, rows, gone = source_ids(), dt.date.today().isoformat(), [], []
    for raw in a.ids:
        i = purge_id(raw)
        cand = [p for p in (ROOT / raw.replace("\\", "/"),) if p.is_file() and p.resolve().is_relative_to(ROOT)]
        target = srcs.get(i) or (cand[0] if cand else None)
        if target is None and not (NOTES / f"{i}.md").exists() and not list(NOTES.rglob(f"{i}.md")):
            sys.exit(f"unknown id or file: {raw} (use a source id, a note id, or a path under inbox/)")
        rows.append(f"{today}\t{purge_hash(i)}\t{a.reason.strip()}")
        if target is not None:
            gone.append(target)
    f = META / "purges.tsv"
    old = f.read_text(encoding="utf-8") if f.exists() else ""
    f.write_text(old + ("" if not old or old.endswith("\n") else "\n") + "\n".join(rows) + "\n", encoding="utf-8", newline="\n")
    for p in gone:
        p.unlink()
        print(f"deleted {p.relative_to(ROOT).as_posix()}")
    if MISSES.exists():
        MISSES.unlink()  # search queries may hold the forgotten words
        print("cleared .cache/search-misses.log")
    print(f"recorded {len(rows)} purge line(s) in meta/purges.tsv (as hashes). Now remove the claims (Edit, no history), "
          "then run `kb.py forget-check <distinctive words>` until it prints 'not found', and `kb.py check`.")
    if a.words:
        a2 = argparse.Namespace(words=a.words)
        print("residue now:")
        cmd_forget_check(a2)


def cmd_forget_check(a):
    """Where do these words still occur in the working tree? (no logging - safe for the forget flow)"""
    words = [wsnorm(w) for w in a.words]
    hits, skipped = [], []
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(x in p.parts for x in (".git", "__pycache__", ".kb-guard")):
            continue
        try:
            t = wsnorm(p.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            if p.suffix.lower() not in (".sqlite", ".pyc"):
                skipped.append(p.relative_to(ROOT).as_posix())
            continue
        except OSError:
            continue
        found = [w for w in words if w in t]  # each word on its own: any hit is a lead
        if found:
            hits.append(f"{p.relative_to(ROOT).as_posix()}: {', '.join(found)}")
    print("\n".join(hits) if hits else "not found in the working tree")
    if skipped:
        print(f"not text, not searched ({len(skipped)}): " + ", ".join(skipped[:10]))
    if (ROOT / ".cache" / "embeddings.sqlite").exists():
        print("note: run `kb.py check` to prune the embedding cache; git history still holds earlier commits")


def cmd_coverage(a):
    """Recall aid for ingest: sentences of a source whose numbers, dates and names no claim citing that source states
    (claims in notes/, inbox/ or meta/parking.md), most fact-like first (language-free signals). Go through them: file
    a claim, or decide it fails the admission test."""
    srcs = source_ids()
    if a.source not in srcs:
        sys.exit(f"unknown source {a.source}")
    body = source_body(srcs[a.source].read_text(encoding="utf-8"))
    citing, quoted = [], []
    for d in (INBOX, NOTES, META / "parking.md"):
        files = md_files(d) if d.is_dir() else ([d] if d.exists() else [])
        for p in files:
            text = p.read_text(encoding="utf-8")
            quoted += [wsnorm(q) for q in QUOTE.findall(text) if len(q) >= MIN_QUOTE]
            citing += [c for _, c in claims(body_of(text)) if any(m.group(1) == a.source for m in CIT.finditer(c))]
    have_n = set().union(*numbers(" ".join(citing)).values()) if citing else set()
    have_d = date_keys(" ".join(citing))
    have_w = {w.casefold() for w in re.findall(r"[^\W\d_][\w-]{2,}", " ".join(citing))}

    def covered(s):
        if any(q in wsnorm(s) or wsnorm(s) in q for q in quoted):
            return True
        n, dk = numbers(s), date_keys(s)
        names = [w.casefold() for w in re.findall(r"(?<=\s)[A-ZÀ-Þ][\w-]+", " " + s)]
        if n or dk:
            same = lambda a, b: a[0] == b[0] and a[2] == b[2] and None in (a[1], b[1]) or a == b
            return all(r & have_n for r in n.values()) and all(any(same(x, h) for h in have_d) for x in dk)
        return bool(names) and sum(w in have_w for w in names) >= 0.6 * len(names)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", body) if len(s.strip()) > 20]
    open_ = [s for s in sentences if not covered(s)]
    score = lambda s: (3 * len(NUM.findall(s)) + 2 * len(re.findall(r"(?<=\s)[A-ZÀ-Þ][\w-]+", s)) + min(len(s), 300) / 100)
    ranked = sorted(open_, key=score, reverse=True)
    for s in ranked[:a.top]:
        print(f"- {s[:220]}")
    more = f" (showing the {a.top} most fact-like; --top N for more)" if len(ranked) > a.top else ""
    print(f"{len(open_)} of {len(sentences)} sentences not covered by a claim citing this source{more}. Judge each in its own language: "
          "most will fail the admission test - that is fine; skip them consciously.")


# ---------------- stats ----------------
def uncited_recent_messages(days=7):
    """Owner messages of the last days that no claim cites - most are chat and tasks; look for a durable one missed."""
    d = SOURCES / "user"
    if not d.exists():
        return []
    cited = {Path(f).stem for f in cited_user_files()}
    since = (dt.date.today() - dt.timedelta(days=days)).isoformat()
    out = []
    for p in sorted(d.glob("*.md"), reverse=True):
        if p.stem[:10] >= since and p.stem not in cited:
            out.append(f"{p.stem}: {' '.join(source_body(p.read_text(encoding='utf-8')).split())[:90]}")
    return out[:8]


def unfinished_filing():
    """A KB change that is not committed: says whether it still needs a review (shown at every session start)."""
    try:
        dig, need, changed = precheck_state()
    except Exception:
        return None
    if not changed:
        return None
    always = str(CFG.get("review", {}).get("mode", "audit")) == "always"
    state = ("needs the reviewer, then kb.py commit" if always and need and not approved(dig)
             else "check it and run kb.py commit")
    return f"{len(changed)} uncommitted KB file(s): {state}"



def cmd_stats(a):
    ids, srcs, today = note_ids(), source_ids(), dt.date.today()
    words, linked, cited, stale = 0, set(), set(), 0
    long_notes, folders = [], Counter()
    for i, p in ids.items():
        fm, body = parse(p)
        n = len(body.split())
        words += n
        if n > 400:
            long_notes.append(i)
        linked |= {m.group(1).strip() for m in LINK.finditer(body)}
        cited |= {m.group(1) for m in CIT.finditer(body)}
        stale += bool(stale_claims(p, srcs, today))
        folders[p.parent.relative_to(NOTES).as_posix()] += 1
    udates = set()
    for p in md_files(HISTORY) + list(ids.values()):
        for m in CIT.finditer(p.read_text(encoding="utf-8")):
            cited.add(m.group(1))
            if m.group(1) == "user" and m.group(2).split():
                udates.add(m.group(2).split()[0])
    cited |= {sid for sid, sp in srcs.items() if sp.parent.name == "user" and any(sid.startswith(d) for d in udates)}
    inbox = [p for p in md_files(INBOX) if "processed" not in p.parts]
    blocked = [p for p in inbox if re.search(r"(?m)^blocked:", p.read_text(encoding="utf-8"))]
    oldest = min((dt.date.fromtimestamp(p.stat().st_mtime) for p in inbox), default=None)
    props = [p.name for p in md_files(META / "proposals") if not re.search(r"(?mi)^status:\s*(done|rejected)", p.read_text(encoding="utf-8"))]
    misses = Counter()
    if MISSES.exists():
        misses = Counter(l.split("\t", 1)[1].strip().lower() for l in MISSES.read_text(encoding="utf-8").splitlines() if "\t" in l)
    hints = [f"folder '{f}' has {n} notes (>40): propose subfolders/hubs" for f, n in folders.items() if n > 40]
    hints += [f"split {n} (>400 words)" for n in sorted(long_notes)]
    gaps = Counter(q.split("->")[-1].strip() for q in misses.elements() if q.startswith("alias-gap"))
    misses = Counter({q: n for q, n in misses.items() if not q.startswith("alias-gap")})
    hints += [f"search missed '{q}' {n}x: alias/title fix or a gap" for q, n in misses.most_common() if n >= 2]
    hints += [f"note {i} found only semantically {n}x: add aliases/summary words (keyword search is the source of truth)" for i, n in gaps.most_common() if n >= 2]
    out = {"notes": len(ids), "words": words, "orphans": len([i for i in ids if i not in linked]),
           "history_files": len(md_files(HISTORY)), "archived": len(md_files(ARCHIVE)),
           "sources": len(srcs), "uncited_sources": len([s for s in srcs if s not in cited and not s.endswith(("-init",))]),
           "notes_with_stale_claims": stale, "inbox_pending": len(inbox), "inbox_blocked": len(blocked),
           "inbox_oldest": str(oldest) if oldest else None, "open_proposals": props[:5],
           "refactor_hints": hints[:5] + ([f"... {len(hints) - 5} more"] if len(hints) > 5 else []),
           "owner_messages_not_filed_7d": uncited_recent_messages(),
           "unfinished_filing": unfinished_filing(),
           "commits_outside_kb_commit": [l for l in git("log", "--format=%h %s", "-n", "200", "--", "notes", "history").splitlines()
                                         if not re.match(r"\w+ kb: ", l)][:5]}
    if a.since:
        days = int(re.sub(r"\D", "", a.since) or 7)
        out["since"] = f"{days} days"
        out["kb_commits"] = [l for l in git("log", f"--since={days}.days", "--format=%ad %s", "--date=short").splitlines() if " kb:" in l][:30]
        out["history_entries_added"] = len([l for l in git("log", f"--since={days}.days", "-p", "--format=", "--", "history/").splitlines()
                                            if l.startswith("+## Superseded")])
    print(json.dumps(out, indent=1))
    if a.stale:
        cmd_stale(a)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("new"); n.add_argument("type"); n.add_argument("id"); n.add_argument("--title", required=True)
    n.add_argument("--summary", required=True); n.add_argument("--today")
    c = sp.add_parser("check"); c.add_argument("--inbox", action="store_true")
    v = sp.add_parser("verify"); v.add_argument("ids", nargs="*")
    v.add_argument("--all", action="store_true", help="every claim of the given notes, not only uncommitted changes (audits)")
    sp.add_parser("precheck")
    s = sp.add_parser("search"); s.add_argument("query"); s.add_argument("--history", action="store_true")
    s.add_argument("--in", dest="scope", help="comma list of: notes (default), history, sources, reports, inbox, work, meta, data")
    s.add_argument("--all", action="store_true", help="every scope: the whole KB except code")
    s.add_argument("--sources", action="store_true"); s.add_argument("-k", type=int, default=8)
    s.add_argument("--keyword", action="store_true", help="keyword (BM25) only - the deterministic source of truth")
    si = sp.add_parser("similar"); si.add_argument("text")
    sp.add_parser("embed")
    se = sp.add_parser("search-eval"); se.add_argument("file"); se.add_argument("--calibrate", action="store_true")
    l = sp.add_parser("links"); l.add_argument("id")
    sa = sp.add_parser("stats"); sa.add_argument("--since"); sa.add_argument("--stale", action="store_true"); sa.add_argument("--today")
    m = sp.add_parser("mv"); m.add_argument("id"); m.add_argument("folder")
    ar = sp.add_parser("archive"); ar.add_argument("id"); ar.add_argument("--reason", required=True)
    fz = sp.add_parser("freeze"); fz.add_argument("path"); fz.add_argument("--kind", default="files",
                                                                        choices=["files", "meetings", "email", "chat", "web"])
    fz.add_argument("--tier", default="2"); fz.add_argument("--title"); fz.add_argument("--slug"); fz.add_argument("--origin")
    fz.add_argument("--date")
    fc = sp.add_parser("forget-check"); fc.add_argument("words", nargs="+")
    sp.add_parser("restore")
    fg = sp.add_parser("forget"); fg.add_argument("ids", nargs="+")
    fg.add_argument("--reason", required=True, choices=["owner-request", "filed-by-mistake", "private", "never-true"])
    fg.add_argument("--words", nargs="*", help="distinctive words of the forgotten content: report where they remain")
    cm = sp.add_parser("commit"); cm.add_argument("-m", "--message", required=True)
    cv = sp.add_parser("coverage"); cv.add_argument("source"); cv.add_argument("--top", type=int, default=25)
    a = ap.parse_args()
    {"new": cmd_new, "check": cmd_check, "verify": cmd_verify, "precheck": cmd_precheck, 
     "search": cmd_search, "links": cmd_links, "stats": cmd_stats, "mv": cmd_mv,
     "archive": cmd_archive, "similar": cmd_similar, "embed": cmd_embed,
     "search-eval": cmd_search_eval, "freeze": cmd_freeze, "forget-check": cmd_forget_check, "forget": cmd_forget, "restore": cmd_restore,
     "commit": cmd_commit, "coverage": cmd_coverage}[a.cmd](a)


if __name__ == "__main__":
    main()
