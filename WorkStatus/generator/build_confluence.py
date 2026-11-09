"""Emit the Confluence body for 🚦 District Ingestion Status (live).

Option A of the two the page was scoped against: the tables that can be live today
are live Jira macros, and the district tables are snapshot-sourced and dated,
structured so each becomes a macro once the Jira district items exist.

The output is an HTML body fragment in the dialect createConfluencePage accepts
(see getContentFormatGuide) — not Confluence storage XML. Run after
build_work_graph.py and build_journey.py, then pass the file to the page tool.
"""
import json
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
TODAY = date.today().isoformat()

SHEET = ("https://docs.google.com/spreadsheets/d/"
         "172NeOz4VwyQdcaNfuY9GjTvxCD3YKGKJAJr7wBR03Rw/edit?usp=sharing")
TRACKER_PAGE = ("https://micollabhub.atlassian.net/wiki/spaces/MiGDL/pages/"
                "6033145857/District+Onboarding+and+Ingestion+Tracker")
ONTOLOGY_PAGE = ("https://ordevista.github.io/MiGDL-DataGov/WorkStatus/"
                 "MiGDL-Work-Ontology.html")
BOARD = ("https://micollabhub.atlassian.net/jira/software/c/projects/MIGDL/boards/857")
BROWSE = "https://micollabhub.atlassian.net/browse/"

ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def e(s):
    return "".join(ESC.get(c, c) for c in str(s if s is not None else ""))


# Column order is the author's, applied to every table so the seven read alike.
COLUMNS = "type,key,summary,assignee,priority,status,updated"


def jira_macro(jql, label):
    """A live Jira issues macro. jqlQuery is evaluated on every page view."""
    params = {"macroParams": {"jqlQuery": {"value": jql},
                              "columns": {"value": COLUMNS},
                              "showSummary": {"value": "true"}},
              "macroMetadata": {"schemaVersion": {"value": "1"},
                                "title": "Jira Legacy"}}
    return ('<div data-type="extension" data-extension-key="jira"'
            ' data-extension-type="com.atlassian.confluence.macro.core"'
            ' data-layout="full-width"'
            " data-parameters='%s'>%s</div>"
            % (json.dumps(params).replace("'", "&apos;"), e(label)))


def toc():
    """Native Table of Contents macro. Levels 2-3 — the h2 sections and the stage and
    sub-table headings under them, which is the whole structure."""
    params = {"macroParams": {"minLevel": {"value": "2"},
                              "maxLevel": {"value": "3"}},
              "macroMetadata": {"schemaVersion": {"value": "1"},
                                "title": "Table of Contents"}}
    return ('<div data-type="extension" data-extension-key="toc"'
            ' data-extension-type="com.atlassian.confluence.macro.core"'
            " data-parameters='%s'></div>" % json.dumps(params))


def keys_jql(keys):
    return "project = MIGDL AND key in (%s) ORDER BY status ASC, key ASC" % ", ".join(keys)


def link(key):
    return '<a href="%s%s">%s</a>' % (BROWSE, key, key)


def table(headers, rows, widths=None):
    out = ['<table data-layout="full-width"><thead><tr>']
    for i, h in enumerate(headers):
        w = ' data-colwidth="%s"' % widths[i] if widths else ""
        out.append("<th%s>%s</th>" % (w, h))
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def panel(kind, html):
    return '<div data-type="panel-%s">%s</div>' % (kind, html)


def lozenge(text, color):
    return ('<span data-type="status" data-color="%s">%s</span>' % (color, e(text)))


def build():
    w = json.loads((OUT / "work.json").read_text())
    j = json.loads((OUT / "journey.json").read_text())
    cov = w["coverage"]
    ds = list(w["districts"].values())
    road = j["road"]
    fixes = j["fixes"]
    notjira = j["notjira"]
    mp = j["map"]

    cited = sorted({k for f in fixes for k in f["claim"]},
                   key=lambda s: int(s.split("-")[1]))
    drifted = sum(1 for r in j["recon"] if r["state"] == "drifted")

    p = []

    # ── how to use ────────────────────────────────────────────────────────
    p.append(toc())
    p.append(panel("info",
        "<p><strong>What this page is.</strong> The engineering view of ingestion: "
        "which pipeline work is moving, what the Data Journey asks for that Jira does "
        "not hold, and which districts are waiting. For the onboarded / in-progress "
        "roll-up by district, use "
        '<a href="%s">🚦 District Onboarding and Ingestion Tracker</a>, which this page '
        "sits beside rather than replaces.</p>"
        "<p><strong>Mixed freshness, deliberately.</strong> Every Jira table below is a "
        "live query — it re-runs when you open the page, so it is never stale. The "
        "district tables are a dated snapshot, because the thing that would make them "
        "live does not exist yet: Jira has no per-district work item to query. Each "
        "snapshot says what it was built from and when.</p>"
        % e(TRACKER_PAGE)))

    p.append("<p><strong>District snapshot taken</strong> "
             '<time datetime="%s">%s</time> · <strong>Jira tables</strong> live · '
             "<strong>Data Journey</strong> %s, dated %s</p>"
             % (w["generated"], w["generated"], e(mp["version"]), e(mp["dated"])))

    p.append(table(
        ["Section", "Freshness", "Becomes live when"],
        [["The road to nightly", lozenge("live", "green"), "— already live"],
         ["The ten fixes", lozenge("live", "green"), "— already live"],
         ["Not in Jira", lozenge("snapshot", "yellow"),
          "the items are raised as issues; the register empties itself"],
         ["Onboarding tickets with no SD code", lozenge("live", "green"),
          "— already live"],
         ["Defects", lozenge("live", "green"), "— already live"],
         ["Districts waiting on Gold", lozenge("snapshot", "yellow"),
          "a Jira item exists per district with its load dates"],
         ["Where district state disagrees", lozenge("snapshot", "yellow"),
          "the four sources collapse to one"]]))

    # ── road to nightly ───────────────────────────────────────────────────
    p.append("<hr>")
    p.append("<h2>🛣️ The road to nightly</h2>")
    p.append("<p>The five stages of the Data Journey's own plan. Each stage's tickets "
             "are listed live, so a stage's progress is read from Jira rather than "
             "transcribed from the map.</p>")

    today = next((r for r in road if r["n"] == 0), None)
    if today:
        p.append(panel("note", "<p><strong>Today.</strong> %s</p>" % e(today["body"])))

    moving = [r for r in road if r["n"] > 0]
    p.append(table(
        ["Stage", "Scope", "What changes", "Stated ETA"],
        [[ "<strong>%d. %s</strong>" % (r["n"], e(r["name"])),
           e(r.get("scope") or "—"),
           e(r.get("teacher") or ""),
           e(r.get("eta") or "No estimate yet")] for r in moving],
        widths=["150", "120", "320", "130"]))

    for r in moving:
        if not r["keys"]:
            continue
        p.append("<h3>%d. %s</h3>" % (r["n"], e(r["name"])))
        p.append("<p>%s</p>" % e(r["body"]))
        p.append(jira_macro(keys_jql(r["keys"]),
                            "Stage %d tickets" % r["n"]))

    # the one observation worth flagging, dated because it is an observation
    s2 = next((r for r in road if r["n"] == 2), None)
    if s2:
        p.append(panel("warning",
            "<p><strong>Worth a conversation at planning.</strong> As of "
            '<time datetime="%s">%s</time>, stage 2 — the batching stage, which the '
            "stated order puts first — had %d tickets with %d done, while stages 3 and "
            "4 were already moving. Stage 2 is gated on %s, which unlocks fix 6. The "
            "live tables above will show whether that is still true.</p>"
            % (w["generated"], w["generated"], s2["tickets"], s2["done"],
               link("MIGDL-658"))))

    # ── the ten fixes ─────────────────────────────────────────────────────
    p.append("<hr>")
    p.append("<h2>🔧 The ten fixes</h2>")
    p.append("<p>The Data Journey names ten fixes against eleven numbered pain points. "
             "The status column is deliberately absent: the map's own chip ages, so "
             "read status from the live table below the fix list.</p>")
    p.append(table(
        ["Fix", "What it does", "Gap group", "Tickets"],
        [["<strong>%d</strong>" % f["n"],
          e(f["head"]),
          e((sorted({r["gap"] for r in j["recon"]
                     if r["fix"] == f["n"] and r.get("gap")}) or ["—"])[0]),
          ", ".join(link(k) for k in sorted(f["claim"],
                                            key=lambda s: int(s.split("-")[1])))
          or "<em>none — see Not in Jira</em>"]
         for f in fixes],
        widths=["60", "300", "180", "220"]))

    p.append("<h3>Every ticket the map cites, live</h3>")
    p.append("<p>%d tickets across the ten fixes. When the map was drawn (%s) %d of "
             "them carried a different status than they do now, which is why this "
             "table is here rather than a picture of the map.</p>"
             % (len(cited), e(mp["jira_asof"]), drifted))
    p.append(jira_macro(keys_jql(cited), "Data Journey tickets"))

    # ── not in Jira ───────────────────────────────────────────────────────
    p.append("<hr>")
    p.append("<h2>🚫 Not in Jira</h2>")
    p.append("<p>Work the map asks for that no Jira query can reach, kept apart by kind "
             "because the remedy differs. This is the only table here that needs a "
             "person rather than a refresh — and the only one that disappears by being "
             "acted on.</p>")
    KIND = {"fix": "Fix with no ticket", "product": "App with no registration option",
            "decision": "Open decision", "broken-ref": "Broken reference"}
    p.append(table(
        ["Kind", "What", "Why it is not in Jira", "Remedy"],
        [[e(KIND.get(x["kind"], x["kind"])), "<strong>%s</strong>" % e(x["what"]),
          e(x["why"]), e(x["remedy"])] for x in notjira],
        widths=["130", "200", "300", "180"]))

    # ── SD codes ──────────────────────────────────────────────────────────
    # Two independent splits, because they call for different actions: a ticket either
    # has a code waiting to be matched or it has none to match, and separately it is
    # either live work or a cancelled duplicate. The 3 Nov backfill emptied the
    # fillable set; new tickets and newly-issued SD codes refill it, so this is
    # computed every build rather than asserted.
    bf = w["sd_backfill"]
    def cancelled(x):
        return "cancel" in (x["status"] or "").lower()
    fillable = [x for x in bf if x["suggested_sd"]]
    unknown = [x for x in bf if not x["suggested_sd"]]
    fill_live = [x for x in fillable if not cancelled(x)]
    unk_live = [x for x in unknown if not cancelled(x)]
    p.append("<hr>")
    p.append("<h2>🔑 Onboarding tickets with no SD code</h2>")
    p.append("<p>The SD code is the join key between a Jira ticket and district state. "
             "A ticket counts as having one if either <code>[MiGDL] SD Code (Auto)</code> "
             "or <code>[MiGDL] SD Code (Manual)</code> is set — Auto is automation-owned "
             "and empty on every onboarding ticket, so Manual is the one people fill in."
             "</p>")
    p.append(panel("info",
        "<p>%d onboarding tickets carry no SD code. They split two ways. <strong>%d can "
        "be filled now</strong> — the district name on the ticket matches a district that "
        "has a code in the Connected Districts master, %d of them on live tickets rather "
        "than cancelled duplicates. The other <strong>%d have no code to match</strong>: "
        "their district carries no SD code anywhere in the master, so someone has to "
        "<strong>issue</strong> one. A bulk backfill on "
        "<time datetime=\"2026-11-03\">3 November 2026</time> filled 24 tickets and left "
        "the fillable set empty; it refills as districts are registered and new tickets "
        "are raised.</p>" % (len(bf), len(fillable), len(fill_live), len(unknown))))
    p.append(jira_macro(
        "project = MIGDL AND issuetype in "
        '("MiGDL District Onboarding (Initial)", "MiGDL District Onboarding (Catch-Up)") '
        "AND cf[10453] IS EMPTY AND cf[10498] IS EMPTY ORDER BY key ASC",
        "Onboarding tickets with no SD code"))

    if fillable:
        p.append("<h3>Can be filled now</h3>")
        p.append("<p>Each district name matches the master, which already holds a code. "
                 "Cancelled duplicates are listed but are not worth filling.</p>")
        p.append(table(
            ["District", "Suggested code", "Ticket", "Status"],
            [[e(x["district"]), "<code>%s</code>" % e(x["suggested_sd"]), link(x["key"]),
              e(x["status"])]
             for x in sorted(fillable, key=lambda x: (x["district"] or "", x["key"]))],
            widths=["260", "130", "120", "200"]))

    if unk_live:
        p.append("<h3>Need a code issued</h3>")
        p.append("<p>Live tickets whose district has no SD code anywhere in the master. "
                 "No match can be made; a code has to be assigned first.</p>")
        p.append(table(
            ["District", "Ticket", "Status"],
            [[e(x["district"]), link(x["key"]), e(x["status"])]
             for x in sorted(unk_live, key=lambda x: (x["district"] or ""))],
            widths=["300", "120", "180"]))

    # ── defects ───────────────────────────────────────────────────────────
    p.append("<hr>")
    p.append("<h2>🐞 Defects</h2>")
    p.append("<p>Live, by status. The "
             '<a href="%s">Kanban board</a> stays the place to work them; this is the '
             "same set in page form so it can be read beside the pipeline work above. "
             "Jira's own issue type is <code>Bug</code>; the Data Journey and this page "
             "call it a defect.</p>" % e(BOARD))
    # Jira's own issue type is Bug; "Defect" is this ontology's name for it, so the
    # macro has to say Bug or it silently returns nothing.
    p.append(jira_macro(
        "project = MIGDL AND issuetype = Bug AND statusCategory != Done "
        "ORDER BY priority DESC, created ASC",
        "Open defects"))

    # ── districts waiting on Gold ─────────────────────────────────────────
    ag = [d for d in ds if d.get("awaiting_gold")]
    ag.sort(key=lambda d: -(d.get("students") or 0))
    by_isd = {}
    for d in ag:
        k = d.get("isd") or "— no ISD recorded —"
        a = by_isd.setdefault(k, [0, 0])
        a[0] += 1
        a[1] += d.get("students") or 0
    p.append("<hr>")
    p.append("<h2>📊 Districts waiting on Gold</h2>")
    p.append(panel("note",
        "<p><strong>This is a queue, not data loss.</strong> %s of %s students in a "
        "connected district are through Gold. The shortfall is %s students across %d "
        "districts whose Bronze, descriptor or Silver load is newer than their Gold "
        "load — the upstream layers have the data and the Gold promotion has not caught "
        "up. Clearing it is what stages 2 and 3 of the road to nightly are for.</p>"
        % (format(cov["students_covered"], ","), format(cov["students_total"], ","),
           format(cov["students_awaiting_gold"], ","), cov["districts_awaiting_gold"])))

    p.append("<h3>By ISD</h3>")
    p.append("<p>Where the backlog sits, so an ISD-level conversation has a number "
             "behind it.</p>")
    p.append(table(
        ["ISD", "Districts waiting", "Students"],
        [[e(k), str(v[0]), format(v[1], ",")]
         for k, v in sorted(by_isd.items(), key=lambda kv: -kv[1][1])],
        widths=["320", "140", "140"]))

    p.append("<h3>The ten largest</h3>")
    p.append(table(
        ["District", "SD code", "Students", "Newest upstream load", "Gold load"],
        [[e(d["name"]), e(d["sd"]), format(d.get("students") or 0, ","),
          e(max([v for k, v in (d.get("stages") or {}).items()
                 if k in ("bronze-load", "descriptor-load", "silver-load")] or ["—"])),
          e((d.get("stages") or {}).get("goldplat-load") or "—")]
         for d in ag[:10]],
        widths=["260", "90", "90", "170", "120"]))

    # ── where state disagrees ─────────────────────────────────────────────
    p.append("<hr>")
    p.append("<h2>🧭 Where district state disagrees</h2>")
    p.append("<p>District state is maintained in four places: Jira, the ingestion "
             "tracker, the Connected Districts master, and the tracker page beside "
             "this one. They do not agree, and this page is a fifth reader of them "
             "rather than a fifth copy. The disagreement is the argument for the Jira "
             "district item.</p>")
    p.append(table(
        ["Measure", "Count", "What it means"],
        [["Districts seen across all sources", str(cov["districts"]),
          "the union, not any one source's total"],
         ["In the ingestion tracker", str(cov["districts_tracker"]), "engineering's list"],
         ["In the Connected Districts master", str(cov["districts_master"]),
          "the authority for identity: SD code, EEM, ISD, SIS, students"],
         ["With at least one Jira ticket", str(cov["districts_with_jira_ticket"]),
          "the rest have no onboarding ticket at all"],
         ["In Jira but not in the tracker", str(cov["districts_jira_only"]),
          "work is happening that the tracker does not show"],
         ["In the master but nowhere else", str(cov["districts_master_only"]),
          "registered, not yet worked"],
         ["Joined to Jira only by name", str(cov["districts_matched_by_name"]),
          "no SD code on the ticket, so the join is a normalised name match"]],
        widths=["300", "90", "330"]))

    byname = [d for d in ds if d.get("matched_by") == "name"]
    if byname:
        # Which tickets actually carry the code is live state, so say only what the
        # join is and point at the fillable table rather than asserting a mechanism.
        p.append("<p>The name-matched districts, down from 12 before the 3 November SD "
                 "code backfill: %s. Each is joined by a normalised name match because "
                 "no ticket for it carries a code; the ones that can be filled from the "
                 "master are listed under <em>Can be filled now</em> above.</p>"
                 % ", ".join("%s (%s)" % (e(d["name"]), e(d["sd"])) for d in byname))

    # ── provenance ────────────────────────────────────────────────────────
    p.append("<hr>")
    p.append("<h2>📄 Where this page comes from</h2>")
    p.append(table(
        ["Source", "Used for", "Freshness"],
        [["Jira project MIGDL", "every live table, and the ticket status in them",
          "live on page view"],
         ['<a href="%s">MAISA Connected Districts spreadsheet</a>' % e(SHEET),
          "district identity, students, ISD, SIS, validation checkpoints",
          "snapshot of %s" % e(w["generated"])],
         ["Ingestion tracker (V2 Results)", "per-layer load dates and next step",
          "snapshot of %s" % e(w["generated"])],
         ["Data Journey (Lucid), %s" % e(mp["version"]),
          "the stations, pain points, ten fixes and the road to nightly",
          "transcribed from the %s export" % e(mp["dated"])],
         ['<a href="%s">MiGDL Work Ontology</a>' % e(ONTOLOGY_PAGE),
          "the same facts in full, across five views: the map, developers, sprint "
          "planning, leadership and K-12 stakeholders. District names are redacted "
          "there; this page is internal and names them.",
          "rebuilt alongside this page"]],
        widths=["260", "320", "160"]))

    p.append(panel("warning",
        "<p><strong>What would make this page fully live.</strong> One thing: a Jira "
        "work item per district carrying its SD code and its six load dates. Every "
        "snapshot table above is then a Jira macro, this page stops having a snapshot "
        "date, and the four sources collapse to one. That is the open grain decision — "
        "whether the district item is per district, per district per school year, or "
        "per district per load. Until it is settled, these tables are dated on purpose."
        "</p>"))

    p.append("<p><em>This page is generated. It is rebuilt from Jira, the tracker and "
             "the master by <code>work-ontology/generator/build_confluence.py</code> in "
             "the MiGDL work-ontology; the full five-view version of the same data lives "
             "in the MiGDL Work Ontology page.</em></p>")

    return "".join(p)


if __name__ == "__main__":
    body = build()
    dest = OUT / "confluence-district-ingestion-status.html"
    dest.write_text(body)
    print("wrote %s  (%d KB)" % (dest.name, len(body) // 1024))
    print("  jira macros", body.count('data-extension-key="jira"'))
    print("  tables     ", body.count("<table"))
    print("  full width ", body.count('data-layout="full-width"'))
