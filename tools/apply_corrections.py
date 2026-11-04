"""Apply reviewer correction files to data/*.json.

Usage: python3 tools/apply_corrections.py <corrections_dir> [--dry-run] [--min-confidence netter-explicit|netter-inferred]

Each <corrections_dir>/corrections_<category>.json has the shape
{"category": ..., "corrections": [{"id", "field", "action", "old", "new", "ref", "reason", "confidence"}], "missing": [...]}
field is "name" | "function" | "pearl" | "details:<Label>".  action "replace" overwrites, "add" appends a new detail
(placed after Innervation / Origin when those exist, otherwise at the end).  A correction whose id is unknown, or whose
"old" no longer matches the current value, is reported and skipped.
"""
import json, pathlib, sys

here = pathlib.Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
dry = "--dry-run" in sys.argv
minconf = "netter-inferred"
if "--min-confidence" in sys.argv:
    minconf = sys.argv[sys.argv.index("--min-confidence") + 1]
cdir = pathlib.Path(args[0])

ORDER_AFTER = {"Blood supply": ["Innervation", "Insertion", "Origin"]}
totals = {"applied": 0, "skipped": 0}
for cat in ["bone", "muscle", "nerve", "lymph", "artery", "vein"]:
    cfile = cdir / f"corrections_{cat}.json"
    if not cfile.exists():
        print(f"{cat}: no corrections file"); continue
    doc = json.load(open(cfile))
    dpath = here / "data" / f"{cat}.json"
    items = json.load(open(dpath))
    byid = {it["id"]: it for it in items}
    applied = skipped = 0
    for c in doc.get("corrections", []):
        if minconf == "netter-explicit" and c.get("confidence") != "netter-explicit":
            skipped += 1; continue
        it = byid.get(c["id"])
        if it is None:
            print(f"  SKIP {cat}/{c['id']}: unknown id"); skipped += 1; continue
        field = c["field"]; new = c["new"]
        if field in ("name", "function", "pearl"):
            if c.get("old") is not None and it.get(field) != c["old"]:
                print(f"  SKIP {cat}/{c['id']}/{field}: current value differs from 'old'"); skipped += 1; continue
            it[field] = new; applied += 1
        elif field.startswith("details:"):
            label = field.split(":", 1)[1]
            existing = next((d for d in it["details"] if d["label"] == label), None)
            if c["action"] == "add" or existing is None:
                if existing is not None:
                    existing["value"] = new
                else:
                    pos = len(it["details"])
                    for anchor in ORDER_AFTER.get(label, []):
                        idx = next((i for i, d in enumerate(it["details"]) if d["label"] == anchor), None)
                        if idx is not None:
                            pos = idx + 1; break
                    it["details"].insert(pos, {"label": label, "value": new})
                applied += 1
            else:
                if c.get("old") is not None and existing["value"] != c["old"]:
                    print(f"  SKIP {cat}/{c['id']}/{field}: current value differs from 'old'"); skipped += 1; continue
                existing["value"] = new; applied += 1
        else:
            print(f"  SKIP {cat}/{c['id']}: unknown field {field}"); skipped += 1
    print(f"{cat}: verified={doc.get('verified')} corrections={len(doc.get('corrections', []))} applied={applied} skipped={skipped} missing={len(doc.get('missing', []))}")
    totals["applied"] += applied; totals["skipped"] += skipped
    if not dry:
        dpath.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n")
print("TOTAL", totals, "(dry run)" if dry else "")
