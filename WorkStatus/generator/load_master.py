"""Load the district master from the MiDX - Connected Districts workbook.

This workbook is upstream of both the Ingestion Tracker Summary and the Confluence
District Onboarding page, so it is the authority for who a district *is*: name, ISD,
SIS, EEM, student count and which applications it is onboarded to, by school year.
The ingestion tracker remains the authority for where a load has got to.

Two deliberate choices:

- The authoritative name is the "District Name" column, not "MiGDL SD Name". The latter
  is maintained by hand and carries at least one copy-paste error: sd20's SD Name is a
  copy of sd37's, though the two are different districts. The engineering tracker joins
  on SD Name, so the error propagates.
- SD codes are stripped, because two of them carry a trailing space which would
  otherwise break an exact-match join.

The workbook's District Contacts tabs hold district staff names and emails. Nothing
here needs them and they are never read.
"""
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "source" / "connected-districts-master.json"
ODS = "2026-2027 ODS Populated Date (completed by Data Engineers)"

APP_COLS = {
    "MiRead SY Onboarded": "miread",
    "MiEWIMS SY Onboarded": "miewims",
    "MiSAFEStudent SY Onboarded": "misafestudent",
    "CSM SY Onboarded": "community-schools-manager",
    "MiStrategy Bank": "mistrategybank",
}
NOT_ENROLLED = {"not enrolled", "", "n/a", "no apps", "no apps yet"}


def _int(v):
    v = (v or "").replace(",", "").strip()
    return int(v) if v.isdigit() else None


def _enrolled(v):
    """The cell holds a school year, a date, or a 'not enrolled' marker."""
    return bool(v) and v.strip().lower() not in NOT_ENROLLED


def load():
    raw = json.loads(SRC.read_text())
    H = {h: i for i, h in enumerate(raw["header"])}

    def g(r, col):
        i = H.get(col)
        return r[i].strip() if i is not None and i < len(r) else ""

    out, no_code = {}, []
    for r in raw["rows"]:
        sd = g(r, "MiGDL SD Code (completed by Data Engineers)").strip()
        name = g(r, "District Name") or g(r, "MiGDL SD Name (completed by Data Engineers)")
        rec = {
            "sd": sd or None,
            "name": name,
            "isd": g(r, "ISD"),
            "sis": g(r, "SIS"),
            "eem": g(r, "EEM Code"),
            "students": _int(g(r, "25-26 Student Count")),
            "ods_populated": g(r, ODS),
            # the ODS date column sometimes records a blocker instead of a date
            "ods_blocked": (g(r, ODS) or "") if not re.match(
                r"^\d{1,2}/\d{1,2}/\d{2,4}$", g(r, ODS) or "") and g(r, ODS) else None,
            "app_ready": g(r, "MiRead/ MiEWIMS District Ready for 2027 Ingestion Date"),
            "agreement_note": g(r, "Agreement Signed") or None,
            "api_active": bool(g(r, "MiGDL API Active")),
            "apps": {slug: g(r, col) for col, slug in APP_COLS.items() if _enrolled(g(r, col))},
            "validation": {
                "b_to_s": g(r, "B->S Validation"),
                "s_to_g": g(r, "S->G Validation"),
                "g_to_p": g(r, "G->P Validation"),
            },
            "historical_needed": [y for y, col in
                                  (("2026", "Historical 2026 Load Needed/\nPriority"),
                                   ("2025", "Historical 2025 Load Needed"),
                                   ("2024", "Historical 2024 Load Needed"))
                                  if g(r, col)],
            "comments": g(r, "Comments"),
        }
        if sd:
            out[sd] = rec
        elif name:
            no_code.append(rec)
    return {"districts": out, "no_sd_code": no_code, "source": raw["source"],
            "tab": raw["tab"], "fetched": raw["fetched"], "spreadsheet": raw["spreadsheet"]}


if __name__ == "__main__":
    import collections
    m = load()
    d = m["districts"]
    print("districts with an SD code  %d" % len(d))
    print("districts without one      %d  (%s)"
          % (len(m["no_sd_code"]), ", ".join(x["name"] for x in m["no_sd_code"][:3]) + " ..."))
    tot = sum(v["students"] or 0 for v in d.values())
    print("students covered           %s" % format(tot, ","))
    print("ISDs                       %d" % len({v["isd"] for v in d.values() if v["isd"]}))
    print("ODS date is a blocker note %d" % sum(1 for v in d.values() if v["ods_blocked"]))
    print("agreement note recorded    %d  %s"
          % (sum(1 for v in d.values() if v["agreement_note"]),
             sorted({v["agreement_note"] for v in d.values() if v["agreement_note"]})))
    print("ODS blocked by a note      %d  %s"
          % (sum(1 for v in d.values() if v["ods_blocked"]),
             sorted({v["ods_blocked"] for v in d.values() if v["ods_blocked"]})))
    print("apps per district          %s"
          % dict(collections.Counter(a for v in d.values() for a in v["apps"])))
    print("historical load needed     %d districts"
          % sum(1 for v in d.values() if v["historical_needed"]))
