"""The MiGDL Delta Operations Game Plan, as structured data.

Transcribed from MiGDL_Delta_Operations_Game_Plan.pdf (Chrome print-to-PDF, Oct 2026),
kept in source/ beside this generator.

A caveat that matters for every number below. The PDF draws its text with 84 Type3
fonts, and only the digits 2, 3, 5, 6 and 9 carry a Unicode mapping anywhere in the
file — 0, 1, 4, 7 and 8 have none. Most digits are still recoverable through each
font's Encoding, but a handful are not, and the filled-vs-hollow compute dots are
indistinguishable in the text layer. Anything unreadable is recorded as None and
rendered as "not readable from the PDF" rather than guessed. The document's own
footer says the throughput figures are estimates to validate against
sys_query_history before being treated as commitments.

`bars_of` groups the eleven job bars onto the four stages by their order in the
drawing, which is an inference from reading order, not something the text states.
"""

TITLE = "MiGDL Delta Operations Game Plan"
LEDE = ("Visualizes operational progress and outcomes, tied to the technical milestones "
        "that unlock each stage, and quantifies the operational KPIs in the scorecard at "
        "right. Each stage gets more correct, more performant, and less compute intensive.")
COMPANION = ("Companion to the Change Handling G1-G6 diagram and the Q4 Plan of Attack.")
CAVEAT = ("Throughput figures are estimates from the Aug 2026 throughput one-pager and two "
          "measured runs; validate against sys_query_history before treating them as "
          "commitments. Draft for team review, Oct 2026.")
UNREADABLE = ("The PDF's text layer has no Unicode mapping for the digits 0, 1, 4, 7 and 8, "
              "and the compute dots are indistinguishable filled from hollow. Figures that "
              "could not be read are marked rather than guessed.")

PIPELINES = [
    {"id": "A", "name": "Bronze & Silver",
     "sub": "per-district tables, no shared writes", "tech": "Spark"},
    {"id": "B", "name": "Gold & Platinum",
     "sub": "one Redshift Serverless cluster · every district writes the same 350 "
            "shared tables", "tech": "Redshift"},
]

# ── the four operating stages ──────────────────────────────────────────────
STAGES = [
    {"n": 0, "name": "Today", "gate": "none (current state)", "eta": None,
     "does": "Deltas only handle inserts and parent-row updates. Any district needing a "
             "child-only update or a delete to propagate gets a full load end-to-end "
             "through A and B.",
     "correct": ["Deltas: inserts + parent updates", "Correct only after a full load"],
     "throughput": ["districts / night", "min stagger, per hr", "vs floor / target"],
     "throughput_readable": False,
     "compute": "Frequent end-to-end full loads, serialized",
     "gates": []},
    {"n": 1, "name": "Deltas through Silver, full loads through Platinum",
     "gate": "G1 + G2 promoted", "eta": "this week (week of 10/19)",
     "does": "Silver now applies child-only updates and deletes, so Pipeline A never needs "
             "a full load except for a new district. Pipeline B drops deltas and runs full "
             "loads only, still one district at a time.",
     "correct": ["All change classes", "A by delta, B by rebuild"],
     "throughput": ["districts / night", "Unchanged — B still one at a time, min stagger"],
     "throughput_readable": False,
     "compute": "A full loads gone; every B run is a rebuild",
     "gates": ["g1g2"]},
    {"n": 2, "name": "End-to-end district batching optimization",
     "gate": "Gold batching lands · Silver scaling resolved",
     "eta": "TBD (higher priority than stage 3)",
     "does": "Two separate optimizations, one per pipeline. Pipeline B full loads run 10-25 "
             "districts per trigger instead of one, collapsing per-district COPY cycles and "
             "write contention at the boundary. Pipeline A should parallelize to any number "
             "of districts (per-district tables, no shared writes), but a spike is uncovering "
             "why it cannot today. Both must land for this stage's KPIs to hold.",
     "correct": ["All change classes", "Same as stage 1"],
     "throughput": ["per night", "Pipeline B at districts / hr per batch at a conservative "
                    "min stagger", "COPYs parallelized regardless of size; sweep time "
                    "insensitive to row volume", "Blocked until Silver scaling is resolved, "
                    "whatever Pipeline B achieves"],
     "throughput_readable": False,
     "compute": "Commits per batch instead of per district. Batched deltas through Gold Main, "
                "full recompute of Derived + Platinum",
     "gates": ["batching", "silverscale"]},
    {"n": 3, "name": "Target state",
     "gate": "G3 + G4 correctness · GM / GD independence",
     "eta": "TBD (gold main deltas could be ready in 3 weeks, independent of stage 2)",
     "does": "Gold main can apply updates and deletes, so it never needs a rebuild. Derived "
             "and Platinum are cleaned and recomputed fully instead of patched by dirty keys "
             "(too many overlapping dependencies). If G3/G4 lands before batching, the "
             "interim is the same shape at 1 district per trigger.",
     "correct": ["All change classes, by delta through GM", "GD / P correct by construction"],
     "throughput": ["per night", "Target GM deltas at / hr — remaining cost is the "
                    "GD / P rebuild"],
     "throughput_readable": False,
     "compute": "Rebuild limited to the projection layer",
     "gates": ["g3g4"]},
]

# ── the gates, tied to the Data Journey's gap groups ───────────────────────
# `fixes` are Data Journey fix numbers, which is how a gate gets a live Jira status.
GATES = {
    "g1g2": {"label": "G1 + G2", "name": "Silver delete handling and child-change handling",
             "unlocks": "Deltas for every change class through Silver.",
             "fixes": [2, 3]},
    "batching": {"label": "Gold batching",
                 "name": "Districts share one COPY and one SQL sweep per batch through Pipeline B",
                 "unlocks": "Throughput one-pager, Aug 2026.",
                 "fixes": [6]},
    "silverscale": {"label": "Silver scaling",
                    "name": "Pipeline A's B→S job runs reliably at the district volume "
                            "Pipeline B can now absorb",
                    "unlocks": "Should parallelize without limit by design; a separate spike "
                               "is finding out why it does not yet.",
                    "fixes": []},
    "g3g4": {"label": "G3 + G4", "name": "Gold update application and delete propagation",
             "unlocks": "Deltas through gold main with no rebuild.",
             "fixes": [4, 5]},
}

# ── the job bars ──────────────────────────────────────────────────────────
# stage -> bars, in drawing order. `hop` is the transition the bar covers.
BARS = {
    0: [
        {"pipe": "A", "hop": "B → S", "n": "1 district", "kind": "Delta",
         "note": "Inserts and parent updates land; child-only updates and deletes do not.",
         "iud": {"I": "yes", "U": "partial", "D": "no"}},
        {"pipe": "A", "hop": "B → S", "n": "1 district", "kind": "Full load",
         "note": "Triggered when a child update or delete must propagate.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
        {"pipe": "B", "hop": "GS → P", "n": "1 district", "kind": "Delta", "tag": "RETIRING",
         "note": "Insert-only through gold main; wasteful when a full load follows anyway.",
         "iud": {"I": "yes", "U": "no", "D": "no"}},
        {"pipe": "B", "hop": "GS → P", "n": "1 district", "kind": "Full load",
         "note": "Whenever Pipeline A needed one; runs in sequence, off hours only.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
    ],
    1: [
        {"pipe": "A", "hop": "B → S", "n": "1 district", "kind": "Delta",
         "note": "All change classes; parallelism across districts is a separate S3 scaling effort.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
        {"pipe": "B", "hop": "GS → P", "n": "1 district", "kind": "Full load",
         "note": "No Pipeline B deltas; 20-min stagger between districts, off hours.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
    ],
    2: [
        {"pipe": "A", "hop": "B → S", "n": "1 district", "kind": "Delta",
         "tag": "SCALING SPIKE",
         "note": "Separate workstream from gold batching. In theory unbounded parallelism; in "
                 "practice the B→S job fails at scale today (spike in progress, no hard "
                 "ceiling yet). Blocks this stage's throughput until resolved.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
        {"pipe": "B", "hop": "GS → P", "n": "10-25 districts", "kind": "Batched full load",
         "note": "One COPY per staging table per batch; a failing district drops out and "
                 "retries solo. Open: batch only the staging COPY (SQL still per district in "
                 "a loop) or batch the Redshift SQL sweep too.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
    ],
    3: [
        {"pipe": "A", "hop": "B → S", "n": "1 district", "kind": "Delta",
         "note": "Unchanged.", "iud": {"I": "yes", "U": "yes", "D": "yes"}},
        {"pipe": "B", "hop": "GS → GM", "n": "10-25 districts", "kind": "Batched delta",
         "note": "New rows only; no gold main rebuilds.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
        {"pipe": "B", "hop": "GD → P", "n": "batch or statewide",
         "kind": "Full projection rebuild",
         "note": "Clean and recompute; batched vs one statewide rebuild under evaluation.",
         "iud": {"I": "yes", "U": "yes", "D": "yes"}},
    ],
}
INDEPENDENCE = "Stages 2 and 3 are independent: either may land first."

# ── open questions the plan itself lists ──────────────────────────────────
DECIDING = [
    {"head": "Where to batch",
     "body": "Batch only the COPY into staging and loop the existing per-district SQL, or "
             "batch the Redshift SQL sweep as well (which requires district and year in "
             "every join and anti-join)."},
    {"head": "GM vs GD/P independence",
     "body": "Scope of the rework to run gold main and the derived layer as separate jobs, "
             "and whether it lands before or conflicts with batching."},
    {"head": "Cost of recompute",
     "body": "Full derived / platinum recompute versus a full gold main refresh, and the "
             "benefit G3/G4 adds on top."},
    {"head": "Linear or not",
     "body": "Derived / platinum rebuild for 10 districts at a time versus one statewide rebuild."},
    {"head": "True bottleneck",
     "body": "Per-step latency in silver-to-gold staging: batch selection, silver read, "
             "staging wipe, flatten, COPY wait."},
    {"head": "Silver scaling",
     "body": "Why the B→S job fails at scale when its design has no shared write targets "
             "(spike in progress, no hard ceiling yet); plus MiDataHub API rate limits."},
]

# ── the layers the bars run between ───────────────────────────────────────
LAYERS = [
    {"code": "B", "name": "Bronze", "store": "S3", "layer": "bronze",
     "desc": "Raw archive, append-only batches, one shared table per entity."},
    {"code": "S", "name": "Silver", "store": "Iceberg", "layer": "silver",
     "desc": "Per district, versioned (currentflag), parent / child / grandchild."},
    {"code": "GS", "name": "Gold Stage", "store": "Redshift", "layer": "goldstage",
     "desc": "200 shared staging tables; the district slice is wiped then COPYed."},
    {"code": "GM", "name": "Gold Main", "store": "Redshift", "layer": "gold-conformed",
     "desc": "Ed-Fi archive (“conf”), 115 statements per district."},
    {"code": "GD", "name": "Gold Derived", "store": "Redshift", "layer": "gold-star",
     "desc": "The MiGDL model (22 marts), 39 statements, cross-entity."},
    {"code": "P", "name": "Platinum", "store": "Redshift", "layer": "platinum",
     "desc": "Application marts (17), 36 statements."},
]
