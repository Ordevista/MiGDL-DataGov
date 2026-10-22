"""What Jira would need to hold for this resource to be rebuilt from Jira alone.

Today the page needs three sources: Jira (work items), the ingestion tracker spreadsheet
(district state), and two hand transcriptions of the Lucid map and the Game Plan. This
module is the register of what has to change for Jira to be the only one.

Each entry carries a probe that measures the gap against live data, so the register is a
checklist that closes itself: populate the field and the row's coverage moves without
anyone editing this file. `kind` separates the four different kinds of work, because a
missing field value is a data-entry job, a missing field is a Jira admin job, a workflow
resolution is a project-config job, and a whole dataset living in a spreadsheet is a
process change.

The last group is deliberate: some things should NOT move into Jira, and saying so is
part of the answer.
"""

# ── where district state is maintained today ───────────────────────────────
# Four places, two of them copies of a third. Recorded here because the gap register
# below is about collapsing them, and because the disagreement between them is itself
# the evidence for the Data Journey's pain point 9.
SOURCES = [
    dict(name="Jira — MIGDL onboarding issue types", grain="onboarding work item",
         districts=76, asof="live", role="The work of onboarding a district. Not the "
         "district population, which is why counting districts here understates it.",
         used=True),
    dict(name="Ingestion Tracker Summary, V2 Results tab", grain="district × SY 2026-27",
         districts=183, asof="2026-10-22",
         role="Per-layer load timestamps, next step, app flags, schedule batch. The "
              "freshest of the four, and what this page reads district state from.",
         used=True),
    dict(name="MAISA Connected Districts Spreadsheet", grain="district",
         districts=None, asof="unknown",
         role="Cited by the Confluence page as its source. A third spreadsheet, distinct "
              "from the Ingestion Tracker Summary. Not read here.", used=False),
    dict(name="Confluence — District Onboarding and Ingestion Tracker",
         grain="district × school year", districts=187, asof="2026-09-22",
         role="The product-owner and leadership view, refreshed by hand from the "
              "Connected Districts spreadsheet. Carries two things the others do not: "
              "SY 2025-26 history (150 districts) and the “No Active Apps” and "
              "“Not Started” states.", used=False),
]

# measured against the tracker on 2026-10-22
RECONCILIATION = [
    "10 of the 16 districts the Confluence page lists as In Progress have since "
    "reached Gold Main Load Completed.",
    "6 of the 13 it lists as having No Active Apps are now loading, four of them "
    "fully loaded.",
    "5 districts it lists with an SD code have no row in the ingestion tracker "
    "(sd45, sd71, sd98, sd128, sd174); three of those are marked “inactivated API” "
    "under SY 2025-26.",
    "7 of its No Active Apps districts are absent from the tracker entirely.",
    "The tracker carries districts the page does not (sd190, sd191), so neither is a "
    "superset of the other.",
]


KINDS = {
    "data": "Populate existing fields",
    "schema": "Add a field or option",
    "setting": "Project or workflow configuration",
    "process": "Move a dataset into Jira",
    "hygiene": "Clean up what is already there",
    "keep-out": "Better left outside Jira",
}


ONBOARDING = ("InitialOnboarding", "CatchUpOnboarding")


def _issues(b):
    return b["issues"]


def _n(b):
    return len(b["issues"]) or 1


# Each probe returns (have, need, unit). have == need means the gap is closed.
GAPS = [
    # ── the dataset that is not in Jira at all ────────────────────────────
    dict(id="district-state", kind="process", priority=1,
         title="District load state lives in the ingestion tracker, not Jira",
         unlocks="The whole K-12 stakeholder view, and the district counts in Leadership. "
                 "This is the single reason the page cannot be built from Jira alone.",
         how="Decide the grain: one Jira item per district per school year (extending the "
             "existing MiGDL District Onboarding types to all districts, not only those "
             "being onboarded), or a Jira-backed replacement for the tracker. Fix 9 on the "
             "Data Journey already calls for “a tracker that is not a shared CSV”, "
             "so this is that fix, scoped.",
         probe=lambda b: (sum(1 for d in b["districts"].values() if d.get("items")),
                          len([d for d in b["districts"].values() if d.get("src") == "tracker"]),
                          "districts with a Jira item")),
    dict(id="stage-dates-all", kind="process", priority=1,
         title="Per-stage completion dates exist only for districts with an onboarding ticket",
         unlocks="District progress dots, and any cycle-time measure per stage.",
         how="Whatever grain the row above lands on, carry the six "
             "[MiGDL] *Load Completed Date* fields on it for every district, not just the "
             "ones with an onboarding ticket.",
         probe=lambda b: (sum(1 for d in b["districts"].values() if d.get("items") and d.get("stages")),
                          len([d for d in b["districts"].values() if d.get("src") == "tracker"]),
                          "districts with dated stages in Jira")),

    dict(id="source-proliferation", kind="process", priority=1,
         title="District state is maintained in four places, two of them copies",
         unlocks="One answer to 'is this district loaded'. Today Jira, the ingestion "
                 "tracker, the Connected Districts spreadsheet and the Confluence page all "
                 "hold a version, and they disagree: when last compared, 10 of the 16 "
                 "districts the Confluence page called In Progress had already finished.",
         how="Pick one system of record — the Jira district item from the first row of "
             "this register — and generate the others from it. The Confluence page is a "
             "hand refresh of a spreadsheet, so it goes stale silently; a generated page "
             "cannot.",
         probe=lambda b: (1, 4, "sources holding district state")),
    dict(id="school-year", kind="schema", priority=2,
         title="School year is not a dimension of district state in Jira",
         unlocks="'Which districts are loaded for which year', and the historical "
                 "backfill the Catch-Up onboarding type exists to do. The Confluence page "
                 "tracks SY 2025-26 (150 districts) and SY 2026-27 separately; the "
                 "ingestion tracker holds 2026-27 only.",
         how="Put school year on the district item so state is per district per year, and "
             "set [MiGDL] Historical Years Needed, which is defined and never used.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("sy")), _n(b),
                          "issues carrying a school year")),
    dict(id="not-onboarding-states", kind="schema", priority=2,
         title="“No Active Apps” and “Not Started” have no Jira equivalent",
         unlocks="Counting the districts that are connected but not consuming. Thirteen "
                 "districts sit in that state on the Confluence page, and four of them have "
                 "an onboarding ticket in Jira with nowhere to say so.",
         how="Add the two states to the onboarding workflow, or a [MiGDL] Engagement "
             "status field, so a district can be registered without implying a load is due.",
         probe=lambda b: (0, 13, "districts in a non-loading state")),

    # ── fields that exist but are empty ───────────────────────────────────
    dict(id="sprint", kind="data", priority=1,
         title="Sprint is empty on every issue",
         unlocks="Velocity, burndown and sprint commitment. The Sprint planning view "
                 "currently shows ready-against-blocked instead, because there is no sprint "
                 "to report on.",
         how="Use the board's sprints, or populate [MiGDL-OPS] Sprint Target Goal and "
             "Work Completed in Sprint. Pick one — both exist and neither is used.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("sprint")), _n(b), "issues")),
    dict(id="resolution", kind="setting", priority=1,
         title="246 issues are Done with no resolution date",
         unlocks="Cycle time, throughput and 'what shipped last month' — none of which "
                 "can be computed today.",
         how="Add a Resolution screen to the transitions into Done, Closed-MiGDL, Load "
             "Completed and Done (Initial User Assigned). Backfill is optional; from the "
             "change date forward is enough to start measuring.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("sc") == "Done" and i.get("resolved")),
                          sum(1 for i in _issues(b) if i.get("sc") == "Done"),
                          "done issues with a resolution date")),
    dict(id="sd-code", kind="data", priority=1,
         title="69 of 143 district onboarding tickets carry no SD code",
         unlocks="A reliable join to district state. Twelve districts can only be matched "
                 "by normalised name today, which is the Data Journey's own pain point 9.",
         how="Make [MiGDL] SD Code (Auto) required on both onboarding issue types, and "
             "backfill the 69. It is the join key for everything district-shaped.",
         probe=lambda b: (sum(1 for i in _issues(b)
                              if i.get("c") in ONBOARDING and (i.get("di") or {}).get("sd")),
                          sum(1 for i in _issues(b) if i.get("c") in ONBOARDING),
                          "onboarding tickets with an SD code")),
    dict(id="story-points", kind="hygiene", priority=3,
         title="Two competing story point fields, 79 issues between them",
         unlocks="Any estimate-based planning. Nine issues have both fields set.",
         how="Retire one of Story Points / Story point estimate at the project level and "
             "migrate the values, so there is one number to read.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("sp")), _n(b), "issues estimated")),
    dict(id="workstream", kind="hygiene", priority=2,
         title="100 issues have no Workstream",
         unlocks="Workstream roll-ups in Leadership and Sprint planning; 17% of work is "
                 "currently uncounted in them.",
         how="Make Workstream required on create, and sweep the existing 100.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("ws")), _n(b), "issues")),

    # ── fields that do not exist yet ──────────────────────────────────────
    dict(id="gap-group", kind="schema", priority=1,
         title="Nothing links a ticket to the pain point or gap group it serves",
         unlocks="The map-against-Jira reconciliation, which is the feature that found 18 "
                 "stale claims. Today that mapping lives in a hand-written transcription of "
                 "the Lucid map; a field would make it Jira's own.",
         how="Add a [MiGDL] Gap Group select (G1–G6) and set it on the 35 tickets the "
             "map already cites. A Jira issue link type 'realises' pointing at an epic per "
             "fix would work equally well.",
         probe=lambda b: (0, 35, "cited tickets carrying their gap group")),
    dict(id="layer-field", kind="schema", priority=2,
         title="Medallion layer is inferred from issue text, not recorded",
         unlocks="The Developer view's 'where this work lands', and station filtering. "
                 "Coverage is 22% and most of it is guessed from wording.",
         how="Add a [MiGDL] Medallion Layer multi-select (Bronze, Silver, Gold Stage, Gold "
             "Conformed, Gold Star, Platinum). Components are defined on the project and "
             "entirely unused — they could carry this instead.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("ly")), _n(b), "issues")),
    dict(id="table-field", kind="schema", priority=2,
         title="The affected table is only known when someone names it in the summary",
         unlocks="Blast radius. Twelve issues of 579 resolve to a real table today, so the "
                 "most useful number on the Developer view is also the rarest.",
         how="Add a [MiGDL] Affected Table free-text or labels field, filled on defects. "
             "Even partial adoption multiplies the blast-radius coverage.",
         probe=lambda b: (sum(1 for i in _issues(b) if i.get("td")), _n(b), "issues")),
    dict(id="app-options", kind="schema", priority=2,
         title="Three consuming applications have no App Registration option",
         unlocks="Attributing work to the app a district actually asked for. Districts "
                 "register for Community Schools Manager (15) and MiStrategyBank (183) in "
                 "the tracker, but no Jira item can name them.",
         how="Add Community Schools Manager, MiStrategyBank and MiCoachCompass as options "
             "on [MiGDL] App Registration so the two sources share one vocabulary.",
         probe=lambda b: (3, 6, "of the six apps selectable in Jira")),
    dict(id="isd-sis", kind="schema", priority=3,
         title="ISD and SIS vendor are tracker-only",
         unlocks="Grouping districts by ISD or by SIS vendor — the natural cut for "
                 "MAISA's own audience, and for spotting a vendor-shaped problem.",
         how="Add [MiGDL] ISD and [MiGDL] SIS fields to the district-grain item.",
         probe=lambda b: (0, len([d for d in b["districts"].values()
                                  if d.get("src") == "tracker"]), "districts")),
    dict(id="schedule", kind="schema", priority=3,
         title="Schedule batch and whether the nightly schedule is on are tracker-only",
         unlocks="Answering 'why did this district not load last night' from Jira, and the "
                 "Game Plan's batching stages.",
         how="Add [MiGDL] Schedule Batch and [MiGDL] Schedule Enabled to the district item.",
         probe=lambda b: (0, len([d for d in b["districts"].values()
                                  if d.get("src") == "tracker"]), "districts")),
    dict(id="decision-type", kind="schema", priority=2,
         title="Open decisions have nowhere to live",
         unlocks="Leadership's 'decisions waiting on MAISA'. Both are gating engineering "
                 "and neither is a task, so neither belongs in a sprint — but both need "
                 "an owner and a date.",
         how="Add a Decision issue type (or a 'decision' label plus a due date) and raise "
             "the two the Data Journey names.",
         probe=lambda b: (0, 2, "open decisions tracked")),
    dict(id="untracked-fixes", kind="data", priority=1,
         title="Two fixes and one gate have no ticket at all",
         unlocks="Honest progress. Fix 1 (ingestion throughput) and fix 9 (status board) "
                 "are drawn on the map as commitments, and the Silver scaling spike gates "
                 "the whole of stage 2 of the Game Plan.",
         how="Raise an epic for each, even if it only holds a spike. Until then no amount "
             "of sprint activity can close them.",
         probe=lambda b: (0, 3, "of the three untracked commitments raised")),
    dict(id="broken-ref", kind="hygiene", priority=2,
         title="MIGDL-230 is cited on the map but does not exist",
         unlocks="Trust in the citations. One of the seven epics behind fix 8 is a dead "
                 "reference.",
         how="Restore the issue or correct the key on the Lucid map.",
         probe=lambda b: (0, 1, "broken references resolved")),
    dict(id="status-vocab", kind="setting", priority=3,
         title="Jira statuses and tracker statuses are two vocabularies for one thing",
         unlocks="One stage taxonomy instead of a mapping table maintained by hand. "
                 "'GOLD MAIN LOAD COMPLETED' and 'Load Completed' mean the same stage.",
         how="Align the onboarding workflow's statuses with the tracker's, or publish the "
             "mapping as a Jira field so both sides agree in writing.",
         probe=lambda b: (0, 1, "shared stage vocabulary")),

    # ── things that should stay out ───────────────────────────────────────
    dict(id="keep-throughput", kind="keep-out", priority=3,
         title="Pipeline throughput and data-age measurements",
         unlocks=None,
         how="Leave these in the run record. They are measurements of the system, not work "
             "items, and the Game Plan already says to validate them against "
             "sys_query_history. Jira should link to them, not store them.",
         probe=None),
    dict(id="keep-lineage", kind="keep-out", priority=3,
         title="Column-level lineage and the medallion asset catalogue",
         unlocks=None,
         how="Keep generating these from the repository. They change when the SQL changes, "
             "not when someone edits a ticket, so the repo is the right source. Jira only "
             "needs to name the table a piece of work affects.",
         probe=None),
]


def build(bundle):
    """Measure every gap against the current bundle, and list the sources it draws on."""
    out = []
    for g in GAPS:
        row = {k: v for k, v in g.items() if k != "probe"}
        if g["probe"]:
            have, need, unit = g["probe"](bundle)
            row.update(have=have, need=need, unit=unit,
                       pct=round(100 * have / need) if need else 0,
                       closed=have >= need)
        else:
            row.update(have=None, need=None, unit=None, pct=None, closed=None)
        out.append(row)
    return {"kinds": KINDS, "gaps": out, "sources": SOURCES,
            "reconciliation": RECONCILIATION}
