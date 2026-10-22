# WorkStatus

MiGDL delivery work mapped onto the pipeline it changes, read five ways.

Open **[MiGDL-Work-Ontology.html](MiGDL-Work-Ontology.html)**.

Jira holds the facts about MiGDL's delivery work, but not the *shape* of it: which
medallion asset a ticket touches, which station of the Data Journey it sits at, which
gate of the Operations Game Plan it unlocks, and which of those four audiences needs to
hear about it. This folder puts the shape in an ontology and makes each audience a
projection of it, so there is one thing to maintain rather than four documents that
drift apart.

## This is a redacted copy

Everything here is public, so it has been redacted. **Individuals appear as the role
they were acting in, districts by SD code, and defect narrative is withheld.** Counts,
statuses, structure and the reconciliation are unchanged, so the views still mean what
they say. [`redaction-manifest.json`](redaction-manifest.json) records exactly what was
removed and why.

Two generator files are deliberately absent, because they contain the material that was
redacted: `journey.py` (the Data Journey transcription, which carries named owners and
quantified defect evidence) and `redact.py` (whose patterns encode the figures it
strips). The remaining scripts rebuild the page from the redacted bundles; they cannot
regenerate the bundles themselves.

## The five views

| View | Reads at | Answers |
|---|---|---|
| **The map** | station | The Data Journey's own layout, with every cited ticket showing live Jira status, plus a register of what the map commits to that Jira cannot track |
| **Game plan** | operating stage | Which stage the operation is in, and whether each gate's tickets have actually landed |
| Developer | table and column | Which asset is affected, how far a change propagates, what blocks what |
| Sprint planning | deliverable | What is ready against what is blocked, and who is carrying it |
| K-12 stakeholder | district and app | Is a district's data in, how old is it, and which apps can use it |

## Where district state comes from

District load state is read from the **ingestion tracker**, not from Jira. Jira's
onboarding issue types track onboarding *work*, which covers a subset: 183 districts
appear in the tracker, 76 have an onboarding ticket, and 4 tickets name a district with
no tracker row at all. Counting districts from Jira alone understates it by more than
half, which is what an earlier version of this page did.

Twelve of those tickets could only be joined to the tracker by a normalised name,
because the Jira ticket carries no SD code. That is the Data Journey's own pain point 9
in miniature — the tracker "matches districts by name" — so the join records which
evidence it used, and the page marks a name match as the weaker one.

`source-ingestion-tracker-v2.redacted.json` is the export the page is built from, with
district names replaced by SD code and EEM codes removed.

## Why it is an ontology and not a report

Three properties do the work that makes a ticket and a lineage node able to answer each
other's questions:

| Property | Joins | Asserted from |
|---|---|---|
| `migdl:touchesTable` | work item → `migdl:Table` | an exact table name in the issue summary — precise and sparse |
| `migdl:targetsLayer` | `migdl:PipelineStage` → `migdl:MedallionLayer` | the stage taxonomy; this is what puts a status on the map |
| `migdl:stationLayer` | `migdl:Station` → `migdl:MedallionLayer` | the Data Journey's own plain-name-over-technical-name pairing |

Loaded with the medallion graph (the same one behind
[`../ontologies/MiGDLAtlas.html`](../ontologies/MiGDLAtlas.html) and
[`../pipeline/MiGDL-Pipeline-Lineage.html`](../pipeline/MiGDL-Pipeline-Lineage.html)),
that lets a defect report its blast radius: a duplicate-rows defect in a Gold dimension
with forty tables downstream is not the same size of problem as one with none. Jira
cannot tell you that; the lineage graph cannot tell you there is a defect.

## Files

| File | What |
|---|---|
| `MiGDL-Work-Ontology.html` | The five-view explorer. Self-contained; no build step, no network calls beyond a web font. |
| `migdl-work.ttl` | Vocabulary: work items, districts, school years, pipeline stages, workstreams, data products, audiences, stations, pain points, fixes, operating stages, gates |
| `migdl-work-instances.ttl` | The work items as instances, redacted |
| `migdl-journey.ttl` | The Data Journey as RDF: stations, pain points, fixes, ticket claims, pipelines, jobs, callouts |
| `migdl-gameplan.ttl` | The Delta Operations Game Plan as RDF: operating stages, gates, job bars, open questions |
| `work.json`, `journey.json`, `gameplan.json` | The bundles the page reads |
| `redaction-manifest.json` | What was removed from the public copy |
| `generator/` | The build scripts, minus the two withheld above |

Vocabularies are standards-first: DCAT for datasets, PROV-O for lineage and for work as
activity, SKOS for the taxonomies, and the `migdl:` namespace only where nothing
standard fits. The namespace does not resolve.

## Rebuilding the page

```sh
python3 generator/build_work_page.py
```

Reads the three bundles in this folder and rewrites the HTML. The full chain — reading
Jira, transcribing the two maps, reconciling and redacting — runs from the private copy.

## Two things the views deliberately say out loud

**The maps go stale, and the page shows by how much.** The Data Journey cites Jira
tickets with the status it was drawn with. Those statuses are compared against Jira as
read, and every one that has moved is marked, along with any cited key that no longer
exists. A static diagram cannot do this; that is the argument for generating the view.

**Where Jira holds nothing, the page says so rather than implying progress.** Fixes with
no ticket, gates with nothing behind them, consuming applications with no registration
field, and decisions that need an owner instead of a ticket are listed as their own
register, kept apart by kind because the remedy differs for each.
