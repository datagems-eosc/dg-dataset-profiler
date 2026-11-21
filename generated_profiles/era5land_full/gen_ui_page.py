"""Build the ERA5-Land profile page in the format of the DataGEMS UI dataset page.

Run from the repo root:  python generated_profiles/era5land_full/gen_ui_page.py OUT.html
Needs era5land_full_profile.json (merge.py) next to this file; the UI stylesheets and
icons in ui/ were taken from the DataGEMS dev UI.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
UI = HERE / "ui"
NOTE = ("The structure, data types, semantic types and samples come from the dataset profiler. "
        "The column statistics were computed over every row of every table, which the deployed "
        "service does not do yet (ENABLE_DB_STATISTICS).")


def svg(body: str) -> str:
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + body + "</svg>")


EXTRA_ICONS = {
    "database": svg('<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5"/><path d="M3 12a9 3 0 0 0 18 0"/>'),
    "table": svg('<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M12 3v18"/>'),
    "rows": svg('<path d="M3 5h18"/><path d="M3 12h18"/><path d="M3 19h18"/>'),
    "hash": svg('<path d="M4 9h16"/><path d="M4 15h16"/><path d="M10 3 8 21"/><path d="M16 3l-2 18"/>'),
    "text": svg('<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>'),
    "list": svg('<path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/>'),
    "alert": svg('<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>'),
}


def main():
    out = Path(sys.argv[1])
    profile = json.load(open(HERE / "era5land_full_profile.json"))
    icons = json.load(open(UI / "icons.json"))
    icons.update(EXTRA_ICONS)
    css = "\n".join(p.read_text() for p in sorted(UI.glob("*.css")))
    payload = json.dumps({"profile": profile, "note": NOTE}, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = (UI / "ui_template.html").read_text()
    html = (html.replace("/*__UI_CSS__*/", css)
                .replace("/*__DATA__*/null", payload)
                .replace("/*__ICONS__*/null", json.dumps(icons).replace("</", "<\\/")))
    out.write_text(html)
    print("wrote", out, round(out.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    main()
