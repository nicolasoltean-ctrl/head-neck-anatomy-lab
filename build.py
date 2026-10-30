#!/usr/bin/env python3
"""Merge data/*.json and splice into template.html.

Outputs:
  index.html       - artifact version (claude.ai adds the document skeleton at publish time)
  site2d/index.html  - standalone 2D version (retired; the hosted site is the 3D lab in site/)
"""
import json, sys, pathlib
here = pathlib.Path(__file__).parent
data_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else here / "data"
items = []
for cat in ["bone", "muscle", "nerve", "lymph", "artery", "vein"]:
    p = data_dir / f"{cat}.json"
    if not p.exists():
        print(f"missing {p}", file=sys.stderr); continue
    arr = json.load(open(p))
    for it in arr:
        it["category"] = cat
    items += arr
    print(cat, len(arr))
ids = [i["id"] for i in items]
assert len(ids) == len(set(ids)), "duplicate ids"
for it in items:
    assert isinstance(it["marker"]["x"], (int, float)) and isinstance(it["marker"]["y"], (int, float)), it["id"]
tpl = (here / "template.html").read_text()
assert tpl.count("/*__DATA__*/[]") == 1
out = tpl.replace("/*__DATA__*/[]", json.dumps(items, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
(here / "index.html").write_text(out)
print("artifact ->", here / "index.html", f"{len(out)//1024} KB")

# ---- standalone site ----
split = out.index('<div class="wrap">')
head_part = out[:split].replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
body_part = out[split:]
favicon = ("data:image/svg+xml," + "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E"
           "%3Crect width='64' height='64' rx='12' fill='%231f6f8b'/%3E"
           "%3Cpath d='M20 50 C14 40 16 24 30 18 C42 13 52 22 50 34 C49 42 44 44 42 48 L36 50 L34 46 L28 46 L26 52 Z' fill='%23f5f0e6'/%3E"
           "%3Ccircle cx='27' cy='29' r='3' fill='%231f6f8b'/%3E%3C/svg%3E")
standalone = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="description" content="Interactive lateral head and neck anatomy plate: identify bones, muscles, nerves, lymphatics, arteries and veins, read each structure's function and a Step 2 CK pearl, or quiz yourself.">
<meta name="color-scheme" content="light dark">
<meta property="og:title" content="Head and Neck Anatomy Lab">
<meta property="og:description" content="Click-to-identify head and neck anatomy with a built-in quiz.">
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
site = here / "site2d"; site.mkdir(exist_ok=True)
(site / "index.html").write_text(standalone)
(site / "robots.txt").write_text("User-agent: *\nAllow: /\n")
(site / "404.html").write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Not found</title><style>body{font:16px system-ui;padding:40px;max-width:40ch}</style></head><body><h1>Page not found</h1><p>The simulator lives at <a href="/">the home page</a>.</p></body></html>\n')
print("standalone ->", site / "index.html", f"{len(standalone)//1024} KB")
