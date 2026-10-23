"""Load the per-district ingestion tracker (V2 Results).

This is the operational system of record for where each district's data has got to.
Jira is not: its onboarding issue types track onboarding *work*, which covers a subset
of the districts the pipeline actually loads. Where the two disagree about a district's
state, the tracker wins and the page says which source a number came from.

The Data Journey's own pain point 9 is that this tracking lives in a shared spreadsheet
that overwrites itself and matches districts by name, so treat it as authoritative for
state but not for history.
"""
import json
import re
from datetime import datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "source" / "ingestion-tracker-v2.json"

# the tracker's status vocabulary mapped onto the ontology's pipeline stages
STAGE_OF_STATUS = {
    "RUNNING - BRONZE LOAD COMPLETED": "bronze-load",
    "DESCRIPTOR LOAD COMPLETED": "descriptor-load",
    "SILVER LOAD COMPLETED": "silver-load",
    "GOLD MAIN LOAD COMPLETED": "complete",
    "GOLD MAIN LOAD COMPLETED - FULL LOAD": "complete",
}
# which column evidences which stage being finished
DATE_COLS = [("Bronze Load", "bronze-load"), ("Descriptor Load", "descriptor-load"),
             ("Silver Load", "silver-load"), ("Gold Load (any type)", "goldplat-load")]
APP_COLS = {"MiRead": "miread", "MiEWIMS": "miewims", "MiSafeStudent": "misafestudent",
            "CommunitySchoolsManager": "community-schools-manager",
            "MiStrategyBank": "mistrategybank"}


def _date(v):
    """The sheet writes M/D/YYYY H:MM; keep the date only."""
    if not v:
        return None
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", v)
    if not m:
        return None
    mo, da, yr = (int(x) for x in m.groups())
    try:
        return datetime(yr, mo, da).strftime("%Y-%m-%d")
    except ValueError:
        return None


def load():
    raw = json.loads(SRC.read_text())
    H = {h: i for i, h in enumerate(raw["header"])}

    def g(r, col):
        i = H.get(col)
        return (r[i].strip() if i is not None and i < len(r) and isinstance(r[i], str)
                else "")

    out = {}
    for r in raw["rows"]:
        sd = g(r, "SD Code")
        if not sd:
            continue
        status = g(r, "Last Entry Status")
        stages = {}
        for col, stage in DATE_COLS:
            d = _date(g(r, col))
            if d:
                stages[stage] = d
        out[sd] = {
            "sd": sd,
            "name": g(r, "SD Name"),
            "isd": g(r, "ISD"),
            "sis": g(r, "SIS"),
            "eem": g(r, "EEM"),
            "school_year": g(r, "School Year"),
            "status": status,
            "stage": STAGE_OF_STATUS.get(status),
            "next_step": g(r, "Next Step"),
            "stages": stages,
            "last_entry": _date(g(r, "Last Entry")),
            "gold_full": _date(g(r, "Most Recent Gold Full Load")),
            "gold_delta": _date(g(r, "Most Recent Gold Delta Load")),
            "products": [slug for col, slug in APP_COLS.items()
                         if g(r, col).upper() == "TRUE"],
            "batch": g(r, "Schedule Batch #"),
            "scheduled": g(r, "Schedule Enabled").upper() == "TRUE",
        }
    return {"districts": out, "source": raw["source"], "tab": raw["tab"],
            "fetched": raw["fetched"], "spreadsheet": raw["spreadsheet"]}


if __name__ == "__main__":
    t = load()
    d = t["districts"]
    import collections
    print("districts      %d" % len(d))
    print("by stage      ", dict(collections.Counter(v["stage"] for v in d.values())))
    print("ISDs           %d" % len({v["isd"] for v in d.values() if v["isd"]}))
    print("scheduled      %d" % sum(1 for v in d.values() if v["scheduled"]))
    print("products      ", dict(collections.Counter(
        p for v in d.values() for p in v["products"])))
    print("unmapped status", sorted({v["status"] for v in d.values() if not v["stage"]}))
