"""Load the six saved Jira MCP result pages into one normalised list of issues.

The MCP tool paginates at 100 and each page exceeded the tool-output limit, so the
harness wrote every page to its own file. Order is by issue key ascending.
"""
import glob, json, os

PAGES = sorted(glob.glob(os.path.join(
    os.environ["JIRA_PAGES"], "mcp-*searchJiraIssuesUsingJql-*.txt")))

# field id -> short ontology name, from the `names` block of a *all fetch
F = {
    "customfield_10471": "load_type",
    "customfield_10461": "app_registration",
    "customfield_10242": "workstream",
    "customfield_10453": "sd_code",
    "customfield_10497": "district_auto",
    "customfield_10459": "eem_code",
    "customfield_10472": "historical_years",
    "customfield_10501": "sy_begin",
    "customfield_10511": "dt_intake",
    "customfield_10512": "dt_bronze",
    "customfield_10513": "dt_descriptor",
    "customfield_10514": "dt_silver",
    "customfield_10515": "dt_goldplat",
    "customfield_10622": "dt_validation",
    "customfield_10517": "data_integrator",
    "customfield_10473": "engineer",
    "customfield_10549": "sprint_goal",
    "customfield_10550": "sprint_work",
    "customfield_10551": "staff_assignments",
    "customfield_10020": "sprint",
    "customfield_10014": "epic_link",
    "customfield_10024": "story_points",
    "customfield_10016": "story_point_estimate",
}


def scalar(v):
    """Jira wraps select options as {value:...} and users as {displayName:...}."""
    if v is None or isinstance(v, (str, int, float)):
        return v
    if isinstance(v, dict):
        for k in ("value", "displayName", "name"):
            if k in v:
                return v[k]
        return None
    if isinstance(v, list):
        got = [scalar(x) for x in v]
        return [g for g in got if g is not None] or None
    return None


def load():
    out, seen = [], set()
    for p in PAGES:
        with open(p) as fh:
            d = json.load(fh)
        nodes = d.get("issues", {}).get("nodes")
        if not nodes:
            continue
        # the very first probe page used a different field set; keep the richer rows
        for n in nodes:
            k = n["key"]
            f = n["fields"]
            if k in seen:
                continue
            seen.add(k)
            par = f.get("parent") or {}
            rec = {
                "key": k,
                "url": n.get("webUrl"),
                "summary": f.get("summary"),
                "type": (f.get("issuetype") or {}).get("name"),
                "hierarchy": (f.get("issuetype") or {}).get("hierarchyLevel"),
                "status": (f.get("status") or {}).get("name"),
                "status_cat": ((f.get("status") or {}).get("statusCategory") or {}).get("name"),
                "priority": (f.get("priority") or {}).get("name"),
                "labels": f.get("labels") or [],
                "assignee": scalar(f.get("assignee")),
                "created": f.get("created"),
                "updated": f.get("updated"),
                "resolved": f.get("resolutiondate"),
                "duedate": f.get("duedate"),
                "parent": par.get("key"),
                "parent_summary": (par.get("fields") or {}).get("summary"),
                "parent_type": ((par.get("fields") or {}).get("issuetype") or {}).get("name"),
                "links": [
                    {"type": (l.get("type") or {}).get("name"),
                     "dir": "out" if l.get("outwardIssue") else "in",
                     "to": (l.get("outwardIssue") or l.get("inwardIssue") or {}).get("key")}
                    for l in (f.get("issuelinks") or [])
                ],
            }
            for cf, name in F.items():
                rec[name] = scalar(f.get(cf))
            out.append(rec)
    return sorted(out, key=lambda r: int(r["key"].split("-")[1]))


if __name__ == "__main__":
    rows = load()
    print(len(rows), "issues", rows[0]["key"], "->", rows[-1]["key"])
