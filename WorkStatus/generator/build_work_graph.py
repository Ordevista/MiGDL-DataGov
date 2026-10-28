#!/usr/bin/env python3
"""Map every MIGDL Jira issue onto the MiGDL work ontology.

Emits:
  migdl-work-instances.ttl   instance graph (Turtle, hand-emitted like gen_rdf.py)
  work.json                  bundle for the audience-view explorer

Every assertion carries its provenance: confidence 1.0 when it was read from a Jira
field, lower when it was inferred from the issue summary. Nothing is invented — an
axis the project does not populate comes out empty and is reported as such.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from load_jira import load  # noqa: E402
import load_tracker  # noqa: E402
import load_master  # noqa: E402

OUT = HERE.parent              # work-ontology/
ROOT = OUT.parent              # the project root, which holds rdf/
ID = "https://migdl.midatahub.org/id/"

# ── the medallion tables we can link work to ────────────────────────────────
MED = (ROOT / "rdf" / "migdl-medallion.ttl").read_text()
TABLES = set(re.findall(r"<https://migdl\.midatahub\.org/id/table/([^>]*)> a migdl:Table", MED))
BARE = defaultdict(set)
for t in TABLES:
    BARE[t.split(".", 1)[1]].add(t)

# table-level lineage, so a work item can report its blast radius: how many tables
# downstream of the one it touches would feel a change to it.
_DF = re.findall(
    r"<https://migdl\.midatahub\.org/id/table/([^>]*)> migdl:derivedFromTable "
    r"<https://migdl\.midatahub\.org/id/table/([^>]*)>", MED)
DOWN = defaultdict(set)          # table -> tables that read from it
for child, parent in _DF:
    DOWN[parent].add(child)
# one block per table: anything up to the next line that starts a new subject
_BLOCK = re.findall(
    r"<https://migdl\.midatahub\.org/id/table/([^>]*)> a migdl:Table(.*?)(?=\n<|\Z)",
    MED, re.S)
TABLE_LAYER = {}
for _name, _body in _BLOCK:
    _m = re.search(r"migdl:inLayer <https://migdl\.midatahub\.org/id/layer/([a-z-]+)>", _body)
    if _m:
        TABLE_LAYER[_name] = _m.group(1)


def blast(table):
    """Transitive downstream closure of one table."""
    seen, stack = set(), [table]
    while stack:
        for nxt in DOWN.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return sorted(seen)

# ── Jira status -> operational stage ────────────────────────────────────────
# Read off the project's real workflow; the statuses ARE the stages.
STAGE_OF_STATUS = {
    "Intake (Initial)": "intake",
    "Connection Setup": "connection-setup",
    "Bronze Load (Catch-Up)": "bronze-load",
    "Descriptor Load (Catch-Up)": "descriptor-load",
    "Silver Load (Catch-Up)": "silver-load",
    "G/P Load (Catch-Up)": "goldplat-load",
    "Validate (Catch-Up)": "validation",
    "Internal Validation": "validation",
    "Ready for Stage": "ready-for-stage",
    "Load Completed": "complete",
    "Done": "complete",
    "Done (Initial User Assigned)": "complete",
    "Closed-MiGDL": "complete",
    "Hold": "blocked",
    "On Hold - DI Follow-Up (Catch-Up)": "blocked",
    "On Hold - DE Follow-Up (Catch-Up)": "blocked",
}
# stage-completion date field -> stage
STAGE_OF_DATE = {
    "dt_intake": "intake", "dt_bronze": "bronze-load",
    "dt_descriptor": "descriptor-load", "dt_silver": "silver-load",
    "dt_goldplat": "goldplat-load", "dt_validation": "validation",
}
STAGE_ORDER = {"blocked": 0, "intake": 1, "connection-setup": 2, "bronze-load": 3,
               "descriptor-load": 4, "silver-load": 5, "goldplat-load": 6,
               "validation": 7, "ready-for-stage": 8, "complete": 9}
STAGE_LAYERS = {
    "connection-setup": ["bronze"], "bronze-load": ["bronze"],
    "descriptor-load": ["silver"], "silver-load": ["silver"],
    "goldplat-load": ["gold-conformed", "gold-star", "platinum"],
}

# ── textual signals (lower confidence than any field) ──────────────────────
LAYER_WORDS = {
    "bronze": ["bronze"],
    "silver": ["silver", "s->g", "s -> g", "b->s", "b -> s"],
    "goldstage": ["goldstage", "gold stage", "staging_"],
    "gold-conformed": ["conformed", "scd2", "_conf", "gold main"],
    "gold-star": ["dim_", "fact_", "star schema"],
    "platinum": ["platinum", "curated_", "g->p", "g -> p", "mart"],
}
DOMAIN_WORDS = {
    "student": ["student"], "enrollment": ["enrollment", "enroll"],
    "assessment": ["assessment", "acadience"], "attendance": ["attendance"],
    "discipline": ["discipline"], "staff": ["staff", "teacher"],
    "calendar": ["calendar", "school year", "schoolyear"],
    "parent-contact": ["parent", "guardian"],
    "education-organization": ["education organization", "eem", "lea", "district roster"],
    "reference-content": ["descriptor"],
    "grades-academic-records": ["grade", "academic record", "transcript"],
    "programs": ["program", "section 504", "special education"],
    "course-section": ["course", "section"],
    "platinum-miread": ["miread"], "platinum-ewims": ["ewims"],
    "cohort-intervention": ["cohort", "intervention"],
}
WORKSTREAM_SLUG = {"Tiger Team": "tiger-team", "Operations": "operations",
                   "Intake": "intake", "API": "api", "Shared": "shared",
                   "MiRead": "miread", "MiEWIMS": "miewims",
                   "MiSAFEStudent": "misafestudent"}
PRODUCT_SLUG = {"MiRead": "miread", "MiEWIMS": "miewims", "MiSAFEStudent": "misafestudent"}
CLASS_OF_TYPE = {
    "Initiative": "Initiative", "Epic": "Epic", "Story": "Deliverable",
    "Task": "Deliverable", "Improvement": "Deliverable", "New Feature": "Deliverable",
    "Bug": "Defect", "Sub-task": "SubTask",
    "MiGDL District Onboarding (Initial)": "InitialOnboarding",
    "MiGDL District Onboarding (Catch-Up)": "CatchUpOnboarding",
}
# the project's own track labels
TRACK = re.compile(r"^TT-\d+$")


# ── personas within the K-12 stakeholder audience ──────────────────────────
# Requested by leadership. A persona changes what is surfaced and how it is worded,
# never the underlying facts.
PERSONAS = [
    {"id": "isd", "label": "ISD Superintendent", "grain": "ISD",
     "asks": "Are the districts in my ISD in the lake, and what will my schools see?",
     "note": "Accountable for a region, not for a load. Reads a roll-up across one ISD, "
             "weighted by students.",
     "omits": "Jira keys, table names and batch numbers \u2014 none of them are actionable "
              "at this grain."},
    {"id": "district", "label": "District Administrator", "grain": "district",
     "asks": "Is my district's data in, how current is it, and what are my teachers seeing?",
     "note": "Reads one row, their own, and needs the plain-language consequence of the "
             "pipeline's known problems.",
     "omits": "The regional roll-up and anything about other districts' status."},
    {"id": "integrator", "label": "Data Integrator", "grain": "work queue",
     "asks": "Which districts need me today, and what is the next action on each?",
     "note": "The one operational persona in this audience: a working queue rather than a "
             "status read, so it keeps the Jira keys and stage detail the other two drop.",
     "omits": "Nothing, except the leadership framing \u2014 this persona is in the "
              "day-to-day."},
]


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")


def tables_in(summary):
    s = (summary or "").lower()
    out = set()
    for bare, full in BARE.items():
        if len(bare) < 6:
            continue
        if re.search(r"(^|[^a-z0-9_])" + re.escape(bare) + r"([^a-z0-9_]|$)", s):
            out |= full
    return sorted(out)


def words_in(summary, mapping):
    s = (summary or "").lower()
    return sorted({k for k, ws in mapping.items() if any(w in s for w in ws)})


def enrich(r):
    """Attach every ontology axis to one issue, each with its provenance."""
    e = dict(r)
    e["class"] = CLASS_OF_TYPE.get(r["type"], "WorkItem")
    e["onboarding"] = e["class"] in ("InitialOnboarding", "CatchUpOnboarding")

    # stage, from the workflow status — a field, so confidence 1.0
    e["stage"] = STAGE_OF_STATUS.get(r["status"])
    e["stage_src"] = "status" if e["stage"] else None

    # stages already finished, from the dated fields
    done = []
    for fld, st in STAGE_OF_DATE.items():
        v = r.get(fld)
        if v:
            done.append({"stage": st, "on": str(v)[:10]})
    e["stages_done"] = sorted(done, key=lambda d: STAGE_ORDER[d["stage"]])

    # layers: from stage (field-derived) then from text (inferred)
    layers = {}
    if e["stage"]:
        for L in STAGE_LAYERS.get(e["stage"], []):
            layers[L] = {"conf": 1.0, "via": "stage:" + e["stage"]}
    for d in e["stages_done"]:
        for L in STAGE_LAYERS.get(d["stage"], []):
            layers.setdefault(L, {"conf": 1.0, "via": "stage-completed:" + d["stage"]})
    for L in words_in(r["summary"], LAYER_WORDS):
        layers.setdefault(L, {"conf": 0.6, "via": "summary"})
    e["layers"] = layers

    # tables: exact name match only, each with its downstream blast radius
    e["tables"] = tables_in(r["summary"])
    e["table_detail"] = [{"t": t, "layer": TABLE_LAYER.get(t), "down": len(blast(t))}
                         for t in e["tables"]]

    # domains: field-backed where the registered app implies a mart, else text
    doms = {}
    for app in (r.get("app_registration") or []) if isinstance(r.get("app_registration"), list) else ([r["app_registration"]] if r.get("app_registration") else []):
        if app == "MiRead":
            doms["platinum-miread"] = {"conf": 1.0, "via": "app-registration"}
        elif app == "MiEWIMS":
            doms["platinum-ewims"] = {"conf": 1.0, "via": "app-registration"}
    for d in words_in(r["summary"], DOMAIN_WORDS):
        doms.setdefault(d, {"conf": 0.6, "via": "summary"})
    e["domains"] = doms

    ws = r.get("workstream")
    ws = ws if isinstance(ws, list) else ([ws] if ws else [])
    e["workstreams"] = [WORKSTREAM_SLUG[w] for w in ws if w in WORKSTREAM_SLUG]
    ap = r.get("app_registration")
    ap = ap if isinstance(ap, list) else ([ap] if ap else [])
    e["products"] = [PRODUCT_SLUG[a] for a in ap if a in PRODUCT_SLUG]
    e["tracks"] = sorted({l for l in r["labels"] if TRACK.match(l)})

    # district identity: prefer the auto fields, fall back to manual
    name = r.get("district_auto")
    e["district"] = {"name": name, "sd": r.get("sd_code"), "eem": r.get("eem_code")} if name or r.get("sd_code") else None

    # audiences — each rule states why this audience cares
    aud = set()
    if e["tables"] or e["layers"] or e["class"] == "Defect":
        aud.add("developer")
    if r["status_cat"] != "Done" and (r["hierarchy"] or 0) <= 0:
        aud.add("sprint-planning")
    if e["class"] in ("Initiative", "Epic") or r["priority"] == "Highest":
        aud.add("leadership")
    if e["onboarding"] or e["products"]:
        aud.add("stakeholder")
    e["audiences"] = sorted(aud)
    return e


# ── Turtle emission ────────────────────────────────────────────────────────
def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def ttl(rows, districts):
    L = ['@prefix migdl: <https://migdl.midatahub.org/ns#> .',
         '@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .',
         '@prefix dct:   <http://purl.org/dc/terms/> .',
         '@prefix prov:  <http://www.w3.org/ns/prov#> .',
         '@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .',
         '', '# Instance graph: MIGDL Jira issues mapped to the MiGDL work vocabulary.',
         '# Generated by ontology/generator/build_work_graph.py — do not edit by hand.', '']

    people = {}
    for r in rows:
        for who in (r.get("assignee"), r.get("data_integrator"), r.get("engineer")):
            if who:
                people[slug(who)] = who

    for s, name in sorted(people.items()):
        L.append('<%sperson/%s> a migdl:Person ; skos:prefLabel "%s" .' % (ID, s, esc(name)))
    L.append("")
    for s, d in sorted(districts.items()):
        parts = ['a migdl:District', 'skos:prefLabel "%s"' % esc(d.get("name") or s)]
        if d.get("sd"):
            parts.append('dct:identifier "%s"' % esc(d["sd"]))
        if d.get("eem"):
            parts.append('migdl:eemCode "%s"' % esc(d["eem"]))
        if d.get("isd"):
            parts.append('migdl:inISD "%s"' % esc(d["isd"]))
        if d.get("sis"):
            parts.append('migdl:sisVendor "%s"' % esc(d["sis"]))
        if d.get("status"):
            parts.append('migdl:trackerStatus "%s"' % esc(d["status"]))
        if d.get("next_step"):
            parts.append('migdl:nextStep "%s"' % esc(d["next_step"]))
        if d.get("batch"):
            parts.append('migdl:scheduleBatch "%s"' % esc(d["batch"]))
        parts.append('migdl:scheduleEnabled %s' % ("true" if d.get("scheduled") else "false"))
        if d.get("stage"):
            parts.append('migdl:atStage <%sstage/%s>' % (ID, d["stage"]))
        for pr in d.get("products", []):
            parts.append('migdl:servesDataProduct <%sproduct/%s>' % (ID, pr))
        L.append('<%sdistrict/%s> %s .' % (ID, s, ' ;\n    '.join(parts)))
    L.append("")

    for r in rows:
        u = "<%swork/%s>" % (ID, r["key"])
        p = ['a migdl:%s' % r["class"],
             'migdl:issueKey "%s"' % r["key"],
             'dct:title "%s"' % esc(r["summary"]),
             'migdl:status "%s"' % esc(r["status"]),
             'migdl:statusCategory "%s"' % esc(r["status_cat"])]
        if r.get("priority"):
            p.append('migdl:priority "%s"' % esc(r["priority"]))
        if r.get("created"):
            p.append('prov:startedAtTime "%s"^^xsd:dateTime' % r["created"][:19])
        sp = r.get("story_points") or r.get("story_point_estimate")
        if sp:
            p.append('migdl:storyPoints %s' % sp)
        if r.get("load_type"):
            p.append('migdl:loadType "%s"' % esc(r["load_type"]))
        if r.get("parent"):
            p.append('migdl:parentWork <%swork/%s>' % (ID, r["parent"]))
        if r.get("assignee"):
            p.append('migdl:assignedTo <%sperson/%s>' % (ID, slug(r["assignee"])))
        if r.get("data_integrator"):
            p.append('migdl:dataIntegrator <%sperson/%s>' % (ID, slug(r["data_integrator"])))
        if r.get("engineer"):
            p.append('migdl:assignedEngineer <%sperson/%s>' % (ID, slug(r["engineer"])))
        for w in r["workstreams"]:
            p.append('migdl:inWorkstream <%sworkstream/%s>' % (ID, w))
        for pr in r["products"]:
            p.append('migdl:servesDataProduct <%sproduct/%s>' % (ID, pr))
        if r.get("district") and r["district"].get("name"):
            p.append('migdl:forDistrict <%sdistrict/%s>'
                     % (ID, r["district"].get("sd") or slug(r["district"]["name"])))
        if r.get("stage"):
            p.append('migdl:atStage <%sstage/%s>' % (ID, r["stage"]))
        for d in r["stages_done"]:
            p.append('migdl:completedStage <%sstage/%s>' % (ID, d["stage"]))
        for t in r["tables"]:
            p.append('migdl:touchesTable <%stable/%s>' % (ID, t))
        for lay in sorted(r["layers"]):
            p.append('migdl:touchesLayer <%slayer/%s>' % (ID, lay))
        for dm in sorted(r["domains"]):
            p.append('migdl:touchesDomain <%sdomain/%s>' % (ID, dm))
        for a in r["audiences"]:
            p.append('migdl:relevantTo <%saudience/%s>' % (ID, a))
        for lk in r["links"]:
            if lk["to"] and lk["type"] == "Blocks" and lk["dir"] == "out":
                p.append('migdl:blocks <%swork/%s>' % (ID, lk["to"]))
            elif lk["to"] and lk["type"] == "Relates":
                p.append('migdl:relatesTo <%swork/%s>' % (ID, lk["to"]))
        L.append('%s %s .' % (u, ' ;\n    '.join(p)))

        # reified stage completions, so each carries its date
        for d in r["stages_done"]:
            L.append('<%swork/%s/stagedone/%s> a migdl:StageCompletion ;\n'
                     '    migdl:ofStage <%sstage/%s> ;\n'
                     '    migdl:completedOn "%s"^^xsd:date ;\n'
                     '    prov:wasGeneratedBy %s .'
                     % (ID, r["key"], d["stage"], ID, d["stage"], d["on"], u))
    return "\n".join(L) + "\n"


def slim(r):
    """Project one enriched issue down to what the explorer page actually renders."""
    return {
        "k": r["key"], "s": r["summary"], "c": r["class"],
        "st": r["status"], "sc": r["status_cat"], "p": r["priority"],
        "ws": r["workstreams"], "stg": r["stage"],
        "sd": r["stages_done"], "td": r["table_detail"],
        "ly": sorted(r["layers"]), "dm": sorted(r["domains"]),
        "di": r["district"], "pr": r["products"],
        "a": r.get("assignee"), "au": r["audiences"],
        "par": r.get("parent"), "tr": r["tracks"],
        "cr": (r.get("created") or "")[:10],
        "sp": r.get("story_points") or r.get("story_point_estimate"),
        "bl": sorted({l["to"] for l in r["links"]
                      if l["to"] and l["type"] == "Blocks" and l["dir"] == "out"}),
    }


def main():
    rows = [enrich(r) for r in load()]

    # Districts come from the ingestion tracker, which is the operational system of
    # record. Jira onboarding tickets are laid on top where they exist; they cover a
    # subset, so counting districts from Jira alone understates the estimate badly.
    tracker = load_tracker.load()
    master = load_master.load()
    dj = {}
    for sd, t in tracker["districts"].items():
        dj[sd] = dict(t, items=[], src="tracker")

    # The master is the authority for who a district is; the tracker for where its load
    # has got to. Districts in the master with no tracker row are real too: they are
    # registered but not yet ingesting, which is the state the Confluence page calls
    # "No Active Apps" and which Jira has no way to record.
    for sd, m in master["districts"].items():
        cur = dj.get(sd)
        if cur is None:
            cur = dj[sd] = {"sd": sd, "status": "", "stage": None, "next_step": "",
                            "stages": {}, "products": [], "batch": "", "scheduled": False,
                            "items": [], "src": "master-only"}
        cur["name"] = m["name"] or cur.get("name") or sd
        cur["isd"] = m["isd"] or cur.get("isd") or ""
        cur["sis"] = m["sis"] or cur.get("sis") or ""
        cur["eem"] = m["eem"] or cur.get("eem")
        cur["students"] = m["students"]
        cur["agreement_note"] = m["agreement_note"]
        cur["ods_blocked"] = m["ods_blocked"]
        cur["app_ready"] = m["app_ready"]
        cur["historical_needed"] = m["historical_needed"]
        cur["validation"] = m["validation"]
        # app registration by school year, which the tracker records only as a flag
        cur["app_sy"] = m["apps"]
        if not cur["products"]:
            cur["products"] = sorted(m["apps"])

    # Jira often carries the district name but no SD code, so fall back to matching on
    # a normalised name. The map's own pain point 9 is that this tracking matches
    # districts by name, so the fallback is recorded as the weaker evidence it is.
    def norm(x):
        return re.sub(r"[^a-z0-9]", "", (x or "").lower())

    by_name = {}
    for sd, t in tracker["districts"].items():
        by_name[norm(t["name"])] = sd
    SUFFIXES = ("schooldistrict", "publicschools", "communityschools", "schools",
                "academy", "isd")

    def match_name(name):
        n = norm(name)
        if n in by_name:
            return by_name[n]
        for suf in SUFFIXES:
            if n.endswith(suf) and n[:-len(suf)] in by_name:
                return by_name[n[:-len(suf)]]
        return None

    jira_only = {}
    for r in rows:
        d = r.get("district")
        if not (d and (d.get("sd") or d.get("name"))):
            continue
        sd = d.get("sd")
        cur = dj.get(sd) if sd else None
        if cur is None and d.get("name"):
            alt = match_name(d["name"])
            if alt:
                cur = dj[alt]
                cur["matched_by"] = "name"
        if cur is None:
            # a district with an onboarding ticket but no row in the tracker
            key = sd or slug(d["name"])
            cur = jira_only.setdefault(key, {
                "sd": sd, "name": d.get("name") or key, "isd": "", "sis": "", "eem": d.get("eem"),
                "status": "", "stage": None, "next_step": "", "stages": {}, "products": [],
                "batch": "", "scheduled": False, "items": [], "src": "jira-only"})
        cur.setdefault("matched_by", "sd-code" if sd else "none")
        cur["items"].append(r["key"])
        # a stage date the ticket evidences that the tracker has not recorded
        for st in r["stages_done"]:
            cur["stages"].setdefault(st["stage"], st["on"])
    dj.update(jira_only)

    (OUT / "migdl-work-instances.ttl").write_text(ttl(rows, dj))

    bundle = {
        "generated": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
        "source": "micollabhub.atlassian.net / project MIGDL",
        "stage_order": STAGE_ORDER,
        "stage_layers": STAGE_LAYERS,
        "issues": [slim(r) for r in rows],
        "districts": dj,
        "coverage": {
            "issues": len(rows),
            "with_stage": sum(1 for r in rows if r["stage"]),
            "with_table": sum(1 for r in rows if r["tables"]),
            "with_layer": sum(1 for r in rows if r["layers"]),
            "with_domain": sum(1 for r in rows if r["domains"]),
            "with_workstream": sum(1 for r in rows if r["workstreams"]),
            "with_district": sum(1 for r in rows if r["district"]),
            "with_product": sum(1 for r in rows if r["products"]),
            "districts": len(dj),
            "districts_tracker": len(tracker["districts"]),
            "districts_with_jira_ticket": sum(1 for v in dj.values() if v["items"]),
            "districts_jira_only": len(jira_only),
            "districts_matched_by_name": sum(
                1 for v in dj.values() if v.get("matched_by") == "name"),
            "districts_master": len(master["districts"]),
            "districts_master_only": sum(1 for v in dj.values() if v["src"] == "master-only"),
            "students_covered": sum(v.get("students") or 0 for v in dj.values()
                                    if v.get("stage") == "complete"),
            "students_total": sum(v.get("students") or 0 for v in dj.values()),
        },
        "personas": PERSONAS,
        "tracker": {k: tracker[k] for k in ("source", "spreadsheet", "tab", "fetched")},
        "master": {k: master[k] for k in ("source", "spreadsheet", "tab", "fetched")},
        # the companion documents a reader jumps to from here
        "companions": {
            "lineage": "https://claude.ai/artifact/PubbBRF6Z77y7VsFYHDTkF",
            "atlas": "https://claude.ai/artifact/CqjSSQmbMS7mDveJXP1XFk",
            "sqlreview": "https://claude.ai/artifact/UFQpiSK9hz8fgFy5fGjoBW",
            "layers": "https://claude.ai/artifact/NJP2jvAuaaHzFtvjPTNdzd",
            "jira": "https://micollabhub.atlassian.net/browse/",
            "board": "https://micollabhub.atlassian.net/jira/software/c/projects/MIGDL/boards/857",
            "ops": "https://micollabhub.atlassian.net/wiki/spaces/MiGDL/pages/6031507476/Operations",
        },
    }
    (OUT / "work.json").write_text(json.dumps(bundle, separators=(",", ":")))

    c = bundle["coverage"]
    print("issues            %d" % c["issues"])
    for k in ("with_stage", "with_table", "with_layer", "with_domain",
              "with_workstream", "with_district", "with_product"):
        print("  %-16s %4d  %5.1f%%" % (k, c[k], 100 * c[k] / c["issues"]))
    print("students          %s of %s in a loaded district"
          % (format(c["students_covered"], ","), format(c["students_total"], ",")))
    print("districts         %d  (master %d, tracker %d, with a Jira ticket %d of which %d matched "
          "only by name, in Jira but not the tracker %d)"
          % (c["districts"], c["districts_master"], c["districts_tracker"],
             c["districts_with_jira_ticket"], c["districts_matched_by_name"],
             c["districts_jira_only"]))
    print("audiences        ", dict(Counter(a for r in rows for a in r["audiences"])))
    print("ttl               %.0f KB" % ((OUT / "migdl-work-instances.ttl").stat().st_size / 1024))
    print("json              %.0f KB" % ((OUT / "work.json").stat().st_size / 1024))


if __name__ == "__main__":
    main()
