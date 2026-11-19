# /// script
# dependencies = ["trafilatura"]
# ///
"""Fetch web documents for case D and convert them to plain text (what an owner would hand over)."""
import sys, urllib.request
from pathlib import Path
import trafilatura

RAW = Path(__file__).parent / "raw"
DOCS = {
    "pg/2021-06-15-pg-versioning-policy.txt": "https://web.archive.org/web/20210615000000*/https://www.postgresql.org/support/versioning/",
    "pg/2023-01-15-pg-versioning-policy.txt": "https://web.archive.org/web/20230115000000*/https://www.postgresql.org/support/versioning/",
    "debian/2023-06-10-debian-12-bookworm-released.en.txt": "https://www.debian.org/News/2023/20230610.en.html",
    "debian/2023-06-10-debian-12-bookworm-uitgebracht.nl.txt": "https://www.debian.org/News/2023/20230610.nl.html",
    "debian/2024-08-14-bullseye-lts-handover.en.txt": "https://www.debian.org/News/2024/20240814.en.html",
}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (case-study fetch)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()


for name, url in DOCS.items():
    if "*/" in url:  # wayback: resolve the closest snapshot via the availability API
        ts, target = url.split("/web/")[1].split("*/")
        url = f"https://web.archive.org/web/{ts[:8]}id_/{target}"
    html, final = get(url)
    text = trafilatura.extract(html, include_tables=True, favor_recall=True) or ""
    p = RAW / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    print(f"{name}: {len(text)} chars from {final}")
