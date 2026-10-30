"""Bangladesh administrative geography, loaded from the same local dataset
the membership application's JavaScript cascade uses
(``static/data/bd/*.json`` — trimmed from techno-stupid/places-in-bangladesh,
no runtime GitHub requests).

Division and District are also modeled here (as plain English-name choice
lists) so the server can validate submitted values from the cascading
selects. Reading directly from the same JSON files the front-end fetches
guarantees the two never drift out of sync (e.g. "Comilla" vs "Cumilla"
spelling differences that would otherwise break form validation).

Upazila is intentionally left out of the server-side choice list — it cascades
from District client-side and is validated only as a plain, non-empty string
(cross-field, in MemberApplicationForm.clean()) rather than against an exact
choice list, since re-deriving the full parent/child validation server-side
isn't needed for this form. Union (the smallest tier, ~4,540 nationwide) is
free text — see README "Known limitations".
"""

import json
import os

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "data", "bd")


def _load(filename):
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


_divisions = _load("divisions.json")
_districts = _load("districts.json")

BD_DIVISIONS = {
    division["name"]: sorted(
        d["name"] for d in _districts if d["division_id"] == division["id"]
    )
    for division in sorted(_divisions, key=lambda d: d["name"])
}

BD_DISTRICTS = sorted({district for districts in BD_DIVISIONS.values() for district in districts})
