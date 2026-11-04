#!/usr/bin/env python3
"""Build the 3D lab.

  python3 build3d.py [mesh_dir]      (default: ./meshes)

<mesh_dir> holds <id>.bin files and manifest.json produced by the Blender exporter (tools/export_meshes.py).
The export is kept in ./meshes (ignored by git, about 24 MB); re-export only to change which structures are included.
Outputs:
  lab3d.html           - artifact page (claude.ai adds the document skeleton); fetches packs/<system>.pack
  packs/<system>.pack  - concatenated meshes per system (published alongside the page)
  docs/index.html + docs/packs/  - standalone copy, published by GitHub Pages from the docs/ folder
"""
import json, sys, pathlib, re, difflib, shutil
here = pathlib.Path(__file__).parent
mesh_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent / "meshes"
man = json.load(open(mesh_dir / "manifest.json"))["meshes"]

# ---------------- cards ----------------
cards = []
for cat in ["bone", "muscle", "nerve", "lymph", "artery", "vein"]:
    for it in json.load(open(here / "data" / f"{cat}.json")):
        it["category"] = cat; cards.append(it)
card_by_id = {c["id"]: c for c in cards}

SYN = [(r"\bbucinator\b", "buccinator"), (r"\bmuscle\b", ""), (r"\bbone\b", ""), (r"\(.*?\)", ""), (r"\bcn [ivx]+ – ", ""),
       (r"scalenus anterior", "anterior scalene"), (r"scalenus medius", "middle scalene"), (r"scalenus posterior", "posterior scalene"),
       (r"\bcolli\b", "cervicis"), (r"crico-arytenoid", "cricoarytenoid"), (r"thyro-arytenoid", "thyroarytenoid"), (r"ary-epiglottic", "aryepiglottic"),
       (r"infra-orbital", "infraorbital"), (r"supra-orbital", "supraorbital"), (r"thyro-epiglottic", "thyroepiglottic"), (r"lymph nodes", "nodes"),
       (r"\bnodes?\b", "nodes"), (r"&", "and"), (r"[’']s?\b", ""), (r"[^a-z0-9 ]", " "), (r"\s+", " ")]
def norm(s):
    s = s.lower()
    for a, b in SYN: s = re.sub(a, b, s)
    return s.strip()
cn = {c["id"]: norm(c["name"]) for c in cards}
alias = {}
for c in cards:
    for part in [c["name"]] + re.split(r" – | / |,", c["name"]):
        alias.setdefault(norm(part), []).append(c["id"])

def find_card(substr, cat=None):
    s = substr.lower()
    hits = [c for c in cards if s in c["name"].lower() and (cat is None or c["category"] == cat)]
    return hits[0]["id"] if hits else None

# manual synonyms: Z-Anatomy label -> (card name substring, category)
MANUAL = {
    "Vertebra C3": ("Typical cervical vertebra", "bone"), "Vertebra C4": ("Typical cervical vertebra", "bone"), "Vertebra C5": ("Typical cervical vertebra", "bone"), "Vertebra C6": ("Typical cervical vertebra", "bone"),
    "Vertebra C7": ("Vertebra prominens", "bone"), "Superior labial artery": ("labial arteries", "artery"), "Inferior labial artery": ("labial arteries", "artery"),
    "Supra-orbital artery": ("Supraorbital and supratrochlear", "artery"), "Supratrochlear artery": ("Supraorbital and supratrochlear", "artery"),
    "Transverse sinus": ("Transverse and sigmoid", "vein"), "Superior ophthalmic vein": ("ophthalmic veins", "vein"), "Superior labial vein": ("Facial vein", "vein"), "Inferior labial veins": ("Facial vein", "vein"),
    "Ophthalmic nerve": ("Ophthalmic division", "nerve"), "Anterior division of mandibular nerve": ("Mandibular division", "nerve"), "Posterior division of mandibular nerve": ("Mandibular division", "nerve"),
    "Vestibular nerve": ("Vestibulocochlear", "nerve"), "Cochlear nerve": ("Vestibulocochlear", "nerve"),
    "Occipitalis muscle": ("Occipitofrontalis", "muscle"), "Frontalis muscle": ("Occipitofrontalis", "muscle"), "Epicranial aponeurosis": ("Occipitofrontalis", "muscle"),
    "Transverse arytenoid muscle": ("Transverse & oblique arytenoids", "muscle"), "Levator nasolabialis": ("alaeque nasi", "muscle"), "Depressor septi nasi": ("Nasalis", "muscle"),
    "Obliquus inferior capitis muscle": ("Suboccipital", "muscle"), "Obliquus superior capitis muscle": ("Suboccipital", "muscle"), "Rectus posterior major capitis muscle": ("Suboccipital", "muscle"), "Rectus posterior minor capitis muscle": ("Suboccipital", "muscle"),
    "Rectus anterior capitis muscle": ("Rectus capitis anterior", "muscle"), "Rectus lateralis capitis muscle": ("Rectus capitis anterior", "muscle"),
    "Thyroid nodes": ("Pretracheal", "lymph"), "Paratracheal cervical nodes": ("Paratracheal", "lymph"), "Intraglandular parotid nodes": ("Deep parotid", "lymph"), "Superficial parotid nodes": ("Preauricular", "lymph"),
    "Infra-auricular nodes": ("Preauricular", "lymph"), "Lateral superior jugular node": ("Level II", "lymph"), "Anterior inferior jugular nodes": ("Level IV", "lymph"), "Inferior deep lateral cervical nodes": ("Supraclavicular", "lymph"), "Bucinator node": ("Facial (buccal)", "lymph"), "Nasolabial node": ("Facial (buccal)", "lymph"),
    "Submental artery": ("Facial artery", "artery"), "Submental vein": ("Facial vein", "vein"), "Basilar venous plexus": ("Inferior petrosal", "vein"), "Occipital sinus": ("Confluence of sinuses", "vein"),
    "Lateral thyrohyoid ligament": ("Hyoid bone", "bone"), "Median thyrohyoid ligament": ("Hyoid bone", "bone"), "Median cricothyroid ligament": ("Cricoid cartilage", "bone"), "Corniculate cartilage": ("Arytenoid cartilages", "bone"), "Quadrangular membrane": ("Epiglottis", "bone"),
    "Lateral temporomandibular ligament": ("Temporomandibular joint", "bone"), "Sphenomandibular ligament": ("Temporomandibular joint", "bone"), "Stylomandibular ligament": ("Temporomandibular joint", "bone"), "Stylohyoid ligament": ("Styloid process", "bone"),
    "Anterior deep temporal artery": ("Maxillary artery", "artery"), "Posterior deep temporal artery": ("Maxillary artery", "artery"), "Buccal artery": ("Maxillary artery", "artery"), "Posterior superior alveolar artery": ("Maxillary artery", "artery"), "Descending palatine artery": ("Greater palatine", "artery"), "Artery of pterygoid canal": ("Maxillary artery", "artery"),
    "Lacrimal artery": ("Ophthalmic artery", "artery"), "Long posterior ciliary arteries": ("Ophthalmic artery", "artery"), "Short posterior ciliary arteries": ("Ophthalmic artery", "artery"), "Septal branches of posterior ethmoidal artery": ("Anterior ethmoidal", "artery"),
    "Anterior cerebral artery": ("Circle of Willis", "artery"), "Posterior cerebral artery": ("Circle of Willis", "artery"), "Middle cerebral artery (M1-segment)": ("Circle of Willis", "artery"), "Anterior inferior cerebellar artery": ("Basilar artery", "artery"), "Posterior inferior cerebellar artery": ("Vertebral artery", "artery"), "Superior cerebellar artery": ("Basilar artery", "artery"), "Anterior spinal artery": ("Vertebral artery", "artery"),
    "Brachiocephalic trunk": ("Common carotid", "artery"), "Aortic arch": ("Common carotid", "artery"), "Deep cervical artery": ("Costocervical", "artery"),
    "Anterior temporal branch": ("Superficial temporal artery", "artery"), "Posterior temporal branch": ("Superficial temporal artery", "artery"),
}

def match_label(label, system):
    if label in MANUAL:
        cid = find_card(MANUAL[label][0], MANUAL[label][1])
        if cid: return cid
    nl = norm(label)
    cands = [c["id"] for c in cards if c["category"] == system]
    if nl in alias:
        same = [cid for cid in alias[nl] if card_by_id[cid]["category"] == system]
        return (same or alias[nl])[0]
    if cands:
        best = difflib.get_close_matches(nl, [cn[c] for c in cands], n=1, cutoff=0.86)
        if best: return next(c for c in cands if cn[c] == best[0])
        for cid in sorted(cands, key=lambda c: -len(cn[c])):
            if len(cn[cid]) >= 6 and (cn[cid] in nl or nl in cn[cid]): return cid
    return None

# ---------------- pack ----------------
packs_dir = here / "packs"; packs_dir.mkdir(exist_ok=True)
for old in packs_dir.glob("*.pack"): old.unlink()
systems = ["skin", "muscle", "bone", "artery", "vein", "nerve", "lymph", "viscera", "cns"]
manifest = {"packs": {}, "center": None, "radius": None, "extent": None}
matched = 0; labels_seen = {}
for sysname in systems:
    items = [m for m in man if m["system"] == sysname]
    if not items: continue
    out = bytearray(); recs = []
    for m in sorted(items, key=lambda x: x["label"]):
        data = (mesh_dir / f"{m['id']}.bin").read_bytes()
        while len(out) % 4: out += b"\0"
        off = len(out); out += data
        card = labels_seen.get((sysname, m["label"]))
        if card is None and (sysname, m["label"]) not in labels_seen:
            card = match_label(m["label"], sysname); labels_seen[(sysname, m["label"])] = card
            if card: matched += 1
        group = card_by_id[card]["group"] if card else ""
        recs.append({"id": m["id"], "label": m["label"], "side": m["side"], "tier": m["tier"], "off": off, "len": len(data), "tris": m["tris"], "card": card, "group": group, "bbox": m["bbox"]})
    (packs_dir / f"{sysname}.pack").write_bytes(out)
    manifest["packs"][sysname] = {"file": f"packs/{sysname}.pack", "bytes": len(out), "meshes": recs}
    print(f"{sysname}: {len(recs)} meshes, {len(out)//1024} KB")
# model frame from skin + bone
boxes = [m["bbox"] for m in man if m["system"] in ("skin", "bone")]
mn = [min(b[i] for b in boxes) for i in range(3)]; mx = [max(b[i + 3] for b in boxes) for i in range(3)]
center = [(mn[i] + mx[i]) / 2 for i in range(3)]; ext = [(mx[i] - mn[i]) / 2 for i in range(3)]
manifest["center"] = [round(c, 4) for c in center]; manifest["extent"] = [round(e, 4) for e in ext]; manifest["radius"] = round(max(ext), 4)
print("labels", len(labels_seen), "with cards", matched, "center", manifest["center"], "radius", manifest["radius"])

# strip bbox from the embedded manifest to keep the page small (kept in packs manifest file)
slim = json.loads(json.dumps(manifest))
for p in slim["packs"].values():
    for r in p["meshes"]: r.pop("bbox", None)
(packs_dir / "manifest.json").write_text(json.dumps(manifest))
# base64 text copies for the artifact host (which serves text but not raw binary)
import base64
b64_dir = here / "packs_b64"; b64_dir.mkdir(exist_ok=True)
for old in b64_dir.glob("*.txt"): old.unlink()
art = json.loads(json.dumps(slim))
for sysname, p in art["packs"].items():
    (b64_dir / f"{sysname}.txt").write_bytes(base64.b64encode((packs_dir / f"{sysname}.pack").read_bytes()))
    p["file"] = f"packs/{sysname}.txt"; p["b64"] = True

# ---------------- splice ----------------
items = []
for cat in ["bone", "muscle", "nerve", "lymph", "artery", "vein"]:
    for it in json.load(open(here / "data" / f"{cat}.json")):
        it["category"] = cat; items.append(it)
tpl = (here / "template3d.html").read_text()
assert tpl.count("/*__DATA__*/[]") == 1 and tpl.count("/*__MANIFEST__*/{}") == 1
j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
out_art = tpl.replace("/*__DATA__*/[]", j(items)).replace("/*__MANIFEST__*/{}", j(art))
(here / "lab3d.html").write_text(out_art)
print("artifact ->", here / "lab3d.html", f"{len(out_art)//1024} KB")
out = tpl.replace("/*__DATA__*/[]", j(items)).replace("/*__MANIFEST__*/{}", j(slim))

# standalone
split = out.index('<div class="wrap">')
head_part = out[:split].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
body_part = out[split:]
favicon = ("data:image/svg+xml," + "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%231f6f8b'/%3E%3Cpath d='M20 50 C14 40 16 24 30 18 C42 13 52 22 50 34 C49 42 44 44 42 48 L36 50 L34 46 L28 46 L26 52 Z' fill='%23f5f0e6'/%3E%3Ccircle cx='27' cy='29' r='3' fill='%231f6f8b'/%3E%3C/svg%3E")
standalone = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Rotatable 3D head and neck anatomy: peel from skin to brain, click any bone, muscle, nerve, vessel or lymph node to identify it, read its function and a Step 2 CK pearl, or quiz yourself.">
<meta name="color-scheme" content="light dark">
<meta property="og:title" content="Head and Neck Simulator">
<meta property="og:type" content="website">
<link rel="icon" href="{favicon}">
<style>
:root {{ color-scheme: light; padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); }}
body {{ margin: 0; font: 14px system-ui, sans-serif; }}
img {{ max-width: 100%; }}
[hidden] {{ display: none !important; }}
</style>
{head_part}</head>
<body>
{body_part}</body>
</html>
"""
site = here / "docs"; site.mkdir(parents=True, exist_ok=True)
(site / "index.html").write_text(standalone)
(site / "robots.txt").write_text("User-agent: *\nAllow: /\n")
(site / "404.html").write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Not found</title><style>body{font:16px system-ui;padding:40px;max-width:40ch}</style></head><body><h1>Page not found</h1><p>The 3D lab lives at <a href="/">the home page</a>.</p></body></html>\n')
if (site / "packs").exists(): shutil.rmtree(site / "packs")
shutil.copytree(packs_dir, site / "packs")
print("standalone ->", site / "index.html")
