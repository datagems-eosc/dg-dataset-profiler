"""Build the self-contained ERA5-Land profile page.

Run from the repo root:  python generated_profiles/era5land_full/gen_page.py OUT.html
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXAMPLE_ROWS = 6
TITLE = "ERA5-Land · full profile"
SUBTITLE = "DataGEMS Dataset Profiler · statistics over all rows"
FOOTER = ("Generated locally with the current profiler, plus database statistics over all rows "
          "(database statistics are switched off in the deployed service).")


def parse_json_str(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return v
    return v


def trim_record_set(rs):
    rs = dict(rs)
    ex = parse_json_str(rs.get("examples"))
    rs["examples"] = ({k: (v[:EXAMPLE_ROWS] if isinstance(v, list) else v) for k, v in ex.items()}
                      if isinstance(ex, dict) else None)
    fields = []
    for f in rs.get("field", []):
        f = dict(f)
        st = dict(f.get("statistics") or {})
        for k in ("histogram", "topValues", "jsonTypes"):
            if k in st:
                st[k] = parse_json_str(st[k])
        f["statistics"] = st
        if isinstance(f.get("sample"), list):
            f["sample"] = f["sample"][:6]
        fields.append(f)
    rs["field"] = fields
    return rs


def main():
    out = Path(sys.argv[1])
    d = json.load(open(HERE / "era5land_full_profile.json"))
    heavy = d["moma_profile_heavy"]
    run = d.get("statisticsRun") or {}
    record_sets = [trim_record_set(rs) for rs in heavy.get("recordSet", [])]
    for rs in record_sets:
        if rs["name"] in run:
            rs["_meta"] = run[rs["name"]]
    record_sets.sort(key=lambda rs: (-(rs.get("_meta") or {}).get("rows", 0), rs["name"]))
    data = {"era5": {
        "dataset": {k: heavy.get(k) for k in ("name", "description", "headline", "keywords", "license",
                                              "country", "datePublished", "fieldOfScience", "inLanguage")},
        "files": [{k: f.get(k) for k in ("@type", "name", "contentSize", "encodingFormat")}
                  for f in heavy.get("distribution", [])],
        "recordSets": record_sets,
        "cdd": d.get("cdd_profile"),
    }}
    payload = json.dumps({"tabs": [{"key": "era5", "label": "ERA5-Land"}], "data": data,
                          "built": date.today().isoformat(), "title": TITLE, "subtitle": SUBTITLE,
                          "footer": FOOTER}, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = (HERE / "page_template.html").read_text()
    out.write_text(html.replace("/*__DATA__*/null", payload))
    print("wrote", out, round(out.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
