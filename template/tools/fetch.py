# /// script
# requires-python = ">=3.12"
# dependencies = ["trafilatura>=1.12"]
# ///
"""fetch - freeze a public web page into sources/web/<id>.md (clean markdown + frontmatter + sha256).

Usage (from KB root):  uv run tools/fetch.py <url> --slug <short-slug> [--tier 1-4] [--today YYYY-MM-DD]
Prints the source id to cite: [src: <id> §Heading "exact quote"]. Refuses to overwrite an existing id.

Egress safety (this command is pre-approved, and pages can carry injected instructions):
- only public http(s) hosts, re-checked on every redirect (no localhost, private or link-local addresses);
- URL and query-string length limits from kb.toml [fetch] (data smuggled out in a URL is refused);
- every fetch is logged to meta/fetch.log, so the owner can see what left the machine.
"""
import argparse, datetime as dt, hashlib, ipaddress, re, socket, sys, urllib.request
from urllib.parse import urlparse
from pathlib import Path


def limits():
    try:
        import tomllib
        f = tomllib.loads(Path("kb.toml").read_text(encoding="utf-8")).get("fetch", {})
    except (OSError, ValueError, ImportError):
        f = {}
    return int(f.get("max_url_length", 300)), int(f.get("max_query_length", 100)), [h.lower() for h in f.get("hosts", [])]


def safe_url(url: str):
    """Only public http(s) URLs: a page cannot make us freeze local files or internal services."""
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        sys.exit(f"refusing {url}: only http(s) URLs")
    max_url, max_query, hosts = limits()
    host = u.hostname.lower()
    if any(len(label) > 40 for label in host.split(".")):
        sys.exit(f"refusing {url}: unusually long host label (data can be smuggled out in hostnames)")
    if hosts and not any(host == h or host.endswith("." + h) for h in hosts):
        sys.exit(f"refusing {host}: not in kb.toml [fetch] hosts - ask the owner to add it")
    if len(url) > max_url:
        sys.exit(f"refusing URL longer than {max_url} characters (kb.toml [fetch] max_url_length)")
    if len(u.query) > max_query:
        sys.exit(f"refusing URL with a query string longer than {max_query} characters - long queries can carry data "
                 "out of the KB (kb.toml [fetch] max_query_length); fetch the page without the query or ask the owner")
    try:
        addrs = {i[4][0] for i in socket.getaddrinfo(u.hostname, None)}
    except OSError as e:
        sys.exit(f"cannot resolve {u.hostname}: {e}")
    for a in addrs:
        ip = ipaddress.ip_address(a.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            sys.exit(f"refusing {url}: {u.hostname} resolves to a non-public address ({ip})")


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)  # every hop must pass the same checks
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url: str) -> str:
    opener = urllib.request.build_opener(SafeRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) kb-fetch"})
    with opener.open(req, timeout=30) as r:
        raw = r.read(10_000_000)
        enc = r.headers.get_content_charset() or "utf-8"
    return raw.decode(enc, "replace")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url"); ap.add_argument("--slug", required=True)
    ap.add_argument("--tier", default="3", choices=["1", "2", "3", "4"]); ap.add_argument("--today")
    ap.add_argument("--dir", default="sources/web")
    a = ap.parse_args()
    d = Path(a.dir).as_posix().lower().rstrip("/")
    if ".." in Path(a.dir).parts or not (d == "sources/web" or d.startswith("sources/web/") or d == "work" or d.startswith("work/")):
        sys.exit("--dir must be sources/web or under work/")
    safe_url(a.url)
    today = a.today or dt.date.today().isoformat()
    slug = re.sub(r"[^a-z0-9-]+", "-", a.slug.lower()).strip("-")
    sid = f"{today}-{slug}"
    out = Path(a.dir) / f"{sid}.md"
    if out.exists():
        sys.exit(f"{out} exists - cite it or choose another slug")
    Path("meta").mkdir(exist_ok=True)
    with open("meta/fetch.log", "a", encoding="utf-8") as log:
        log.write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S}\t{a.url}\n")
    try:
        html = download(a.url)
    except SystemExit:
        raise
    except Exception as e:
        sys.exit(f"could not fetch {a.url}: {e}")
    import trafilatura  # imported late: URL checks above work without the dependency
    body = trafilatura.extract(html, output_format="markdown", include_links=False, include_tables=True,
                               favor_precision=True)
    if not body or len(body.split()) < 50:
        sys.exit(f"extracted too little text from {a.url} - try another page")
    meta = trafilatura.extract_metadata(html)
    clean = lambda v, dflt: re.sub(r"[\r\n\"]+", " ", v).strip()[:200] if v else dflt
    title, author = clean(meta.title if meta else None, slug), clean(meta.author if meta else None, "unknown")
    published = meta.date if meta and meta.date and re.match(r"\d{4}-\d{2}-\d{2}$", meta.date) else "unknown"
    sha = hashlib.sha256(body.rstrip("\n").encode("utf-8")).hexdigest()[:16]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""---
id: {sid}
type: web
title: "{title}"
origin: {a.url}
author: "{author}"
published: {published}
retrieved: {today}
sha256: {sha}
tier: {a.tier}
---
{body}
""", encoding="utf-8", newline="\n")
    print(f"saved {out.as_posix()} ({len(body.split())} words). Cite as [src: {sid} §<heading> \"exact quote\"]")


if __name__ == "__main__":
    main()
