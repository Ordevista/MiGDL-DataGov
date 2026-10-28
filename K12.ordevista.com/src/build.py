#!/usr/bin/env python3
"""Build the Ordevista resources landing page.

Reads content/resources.json, writes a static site to dist/.
No third-party dependencies, no trackers, no external requests from the page.

  python3 src/build.py            # build
  python3 src/build.py --strict   # fail if a listed file is missing
"""
import datetime as dt
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
SRC = ROOT / "src"
DIST = ROOT / "dist"

esc = html.escape


def fmt_date(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def card(item, today, warnings):
    title = esc(item["title"])
    desc = esc(item.get("description", ""))
    kind = esc(item.get("type", "Link"))
    href = item.get("url")
    badge = item.get("badge")
    state = "open"

    if item.get("file"):
        if (CONTENT / "files" / item["file"]).is_file():
            href = "files/" + item["file"]
        else:
            warnings.append(f"missing file: content/files/{item['file']}  ({item['title']})")
            href, badge, state = None, "Coming soon", "soon"

    if item.get("expires") and dt.date.fromisoformat(item["expires"]) < today:
        href, badge, state = None, f"Closed {fmt_date(item['expires'])}", "closed"

    if not href and state == "open":
        state = "soon"

    meta = [kind]
    if item.get("owner"):
        meta.append(esc(item["owner"]))
    if item.get("date"):
        meta.append(fmt_date(item["date"]))
    meta_html = " · ".join(meta)

    logo = ""
    if item.get("logo"):
        logo = (f'<img class="logo" src="assets/logos/{esc(item["logo"])}" '
                f'alt="" width="240" height="72" loading="lazy">')
    domain = f'<p class="domain">{esc(item["domain"])}</p>' if item.get("domain") else ""
    badge_html = f'<span class="badge badge-{state}">{esc(badge)}</span>' if badge else ""
    # Every resource link (external sites and our own PDFs) opens in a new tab,
    # so the resource list stays open behind it.
    link_attr = ' target="_blank" rel="noopener noreferrer"'
    link_hint = '<span class="sr-only"> (opens in a new tab)</span>'

    heading = (f'<a href="{esc(href)}"{link_attr}>{title}{link_hint}</a>' if href
               else f"<span>{title}</span>")
    classes = "card" + (" featured" if item.get("featured") else "") + f" state-{state}"
    search = esc(" ".join(str(item.get(k, "")) for k in
                          ("title", "description", "type", "owner", "domain")).lower())
    return f"""
      <li class="{classes}" data-search="{search}">
        {logo}
        <p class="meta">{meta_html}</p>
        <h3>{heading}</h3>
        <p class="desc">{desc}</p>
        {domain}
        {badge_html}
      </li>"""


def build(strict=False):
    data = json.loads((CONTENT / "resources.json").read_text(encoding="utf-8"))
    site = data["site"]
    today = dt.date.today()
    warnings = []

    nav, sections = [], []
    for s in data["sections"]:
        nav.append(f'<a href="#{esc(s["id"])}">{esc(s["title"])}</a>')
        cards = "".join(card(i, today, warnings) for i in s["items"])
        intro = f'<p class="section-intro">{esc(s["intro"])}</p>' if s.get("intro") else ""
        sections.append(f"""
    <section id="{esc(s['id'])}" aria-labelledby="{esc(s['id'])}-h">
      <h2 id="{esc(s['id'])}-h">{esc(s['title'])}</h2>
      {intro}
      <ul class="grid" role="list">{cards}
      </ul>
    </section>""")

    page = (SRC / "template.html").read_text(encoding="utf-8")
    replacements = {
        "{{TITLE}}": esc(site["title"]),
        "{{ORG}}": esc(site["org"]),
        "{{TAGLINE}}": esc(site["tagline"]),
        "{{INTRO}}": esc(site["intro"]),
        "{{NAV}}": "\n        ".join(nav),
        "{{SECTIONS}}": "".join(sections),
        "{{EMAIL}}": esc(site["contact_email"]),
        "{{BASE_URL}}": esc(site["base_url"]),
        "{{UPDATED}}": fmt_date(today.isoformat()),
        "{{YEAR}}": str(today.year),
    }
    for k, v in replacements.items():
        page = page.replace(k, v)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(page, encoding="utf-8")
    for name in ("styles.css", "app.js", "404.html", "robots.txt"):
        shutil.copy2(SRC / name, DIST / name)
    shutil.copytree(CONTENT / "assets", DIST / "assets")
    shutil.copy2(CONTENT / "assets" / "favicon.ico", DIST / "favicon.ico")  # browsers request /favicon.ico
    if (CONTENT / "pages").is_dir():  # extra pages, e.g. content/pages/maeds-2026/index.html
        shutil.copytree(CONTENT / "pages", DIST, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".*"))
    files = [f for f in (CONTENT / "files").iterdir() if not f.name.startswith(".")]
    (DIST / "files").mkdir()
    for f in files:
        shutil.copy2(f, DIST / "files" / f.name)

    for w in warnings:
        print("WARNING:", w, file=sys.stderr)
    if strict and warnings:
        sys.exit("Strict build failed: listed files are missing.")
    print(f"Built dist/ ({len(files)} file(s) in files/, {len(warnings)} warning(s))")


if __name__ == "__main__":
    build(strict="--strict" in sys.argv)
