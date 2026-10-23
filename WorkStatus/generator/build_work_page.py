#!/usr/bin/env python3
"""Compose the MiGDL Work Ontology page from the template, script and bundles."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
# --public builds from the redacted bundles in public/ into that same folder
PUBLIC = "--public" in sys.argv
SRC = (OUT / "public") if PUBLIC else OUT

work = json.loads((SRC / "work.json").read_text())
jrny = json.loads((SRC / "journey.json").read_text())
gplan = json.loads((SRC / "gameplan.json").read_text())

sys.path.insert(0, str(HERE))
import jira_gaps  # noqa: E402
gaps = jira_gaps.build(work)

# triple count across the whole union graph, so the footer figure is real
try:
    from rdflib import Graph
    g = Graph()
    for f in ("../rdf/migdl-ontology.ttl", "../rdf/migdl-medallion.ttl",
              "migdl-work.ttl", "migdl-work-instances.ttl", "migdl-journey.ttl",
              "migdl-gameplan.ttl"):
        base = OUT if f.startswith("..") else SRC
        g.parse(str((base / f).resolve()), format="turtle")
    triples = "{:,}".format(len(g))
except Exception as e:                      # rdflib is optional for the page build
    print("  (triple count skipped: %s)" % e)
    triples = "n/a"

drift = sum(1 for r in jrny["recon"] if r["state"] == "drifted")

html = (HERE / "work_page.html").read_text()
sub = {
    "{{BUNDLE}}": json.dumps(work, separators=(",", ":")),
    "{{JOURNEY}}": json.dumps(jrny, separators=(",", ":")),
    "{{GAMEPLAN}}": json.dumps(gplan, separators=(",", ":")),
    "{{GAPS}}": json.dumps(gaps, separators=(",", ":")),
    "{{SCRIPT}}": (HERE / "work_script.js").read_text(),
    "{{NITEMS}}": "{:,}".format(work["coverage"]["issues"]),
    "{{NDIST}}": str(work["coverage"]["districts"]),
    "{{NTRIPLES}}": triples,
    "{{NDRIFT}}": str(drift),
    "{{NCLAIM}}": str(len(jrny["recon"])),
    "{{GEN}}": work["generated"],
    "{{MAPVER}}": jrny["map"]["version"],
    "{{MAPDATE}}": jrny["map"]["dated"],
    "{{MAPASOF}}": jrny["map"]["jira_asof"],
    "{{BOARD}}": work["companions"]["board"],
    "{{OPS}}": work["companions"]["ops"],
}
if PUBLIC:
    banner = ('<div class="gap" style="border-left-color:var(--accent);'
              'background:var(--accent-soft);margin:0">'
              '<b>Redacted copy.</b> Individuals appear as the role they were acting in, '
              'districts by SD code, and defect narrative is withheld. '
              'Counts, statuses and structure are unchanged. '
              'See <code>redaction-manifest.json</code> for exactly what was removed.</div>')
    html = html.replace('<main class="wrap" id="view"></main>',
                        '<div class="wrap" style="padding-block:14px 0">' + banner +
                        '</div>\n<main class="wrap" id="view"></main>')

for k, v in sub.items():
    html = html.replace(k, v)

left = [k for k in sub if k in html]
if left:
    raise SystemExit("unsubstituted placeholders: %s" % left)
if "{{" in html:
    raise SystemExit("a placeholder survived: %s" % html[html.index("{{"):][:40])

dest = SRC / "MiGDL-Work-Ontology.html"
dest.write_text(html)
print("wrote %s  (%.0f KB)" % (dest.name, dest.stat().st_size / 1024))
print("  work items %s | districts %s | triples %s | stale claims %s/%s"
      % (sub["{{NITEMS}}"], sub["{{NDIST}}"], triples, drift, len(jrny["recon"])))
