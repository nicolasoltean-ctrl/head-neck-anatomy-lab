"""Split fused Z-Anatomy curves into their named branches.

  python3 tools/split_branches.py            (run from the project root; pure Python, no Blender needed)

Many Z-Anatomy nerves and vessels are ONE curve object holding several splines: the trunk and its branches.
tools/export_splines.py (Blender) writes every spline as its own tube mesh into meshes/splines/, with its
centreline in meshes/splines/splines.json. This script reads data/branches.json, which names each spline, or a
stretch of a spline between two fractions of its length, and replaces the fused mesh in meshes/manifest.json
with one mesh per named piece. Pieces that are not named keep the parent's label, so nothing is lost.

data/branches.json:
  { "<source label>": [ {"spline": 3, "label": "..."},                      whole spline(s): int or list
                        {"spline": 0, "from": 0.54, "to": 0.64, "label": "..."} ] }   a stretch of one spline
Fractions run along the spline's control polyline from its first control point (0) to its last (1); they are the
same fractions tools' spline report prints as "parent_at". The right side reuses the left side's numbering after
checking that the two sides mirror each other.
"""
import json, math, struct, pathlib, sys

here = pathlib.Path(__file__).resolve().parent.parent
SPL = here / "meshes" / "splines"
spec = json.load(open(here / "data" / "branches.json"))
splines = json.load(open(SPL / "splines.json"))
man_path = here / "meshes" / "manifest.json"
man = json.load(open(man_path))

def read_bin(path):
    b = open(path, "rb").read()
    nV, nI = struct.unpack_from("<II", b, 4); mn = struct.unpack_from("<3f", b, 12); mx = struct.unpack_from("<3f", b, 24)
    q = struct.unpack_from("<%dh" % (nV * 3), b, 36)
    verts = [tuple(mn[a] + (q[i * 3 + a] + 32767) / 65534 * (mx[a] - mn[a]) for a in range(3)) for i in range(nV)]
    idx = struct.unpack_from("<%d%s" % (nI, "I" if nV > 65535 else "H"), b, 36 + nV * 6)
    return verts, idx

def write_bin(path, verts, idx):
    n = len(verts)
    mn = [min(v[a] for v in verts) for a in range(3)]; mx = [max(v[a] for v in verts) for a in range(3)]
    rng = [max(mx[a] - mn[a], 1e-9) for a in range(3)]
    q = bytearray()
    for v in verts: q += struct.pack("<3h", *[int(round((v[a] - mn[a]) / rng[a] * 65534 - 32767)) for a in range(3)])
    with open(path, "wb") as f:
        f.write(b"HNM1"); f.write(struct.pack("<II", n, len(idx))); f.write(struct.pack("<6f", *mn, *mx)); f.write(q)
        f.write(struct.pack("<%d%s" % (len(idx), "I" if n > 65535 else "H"), *idx))
    return {"verts": n, "tris": len(idx) // 3, "bbox": [round(x, 4) for x in mn + mx], "bytes": path.stat().st_size}

def densify(ctrl, step=0.001):
    out = [tuple(ctrl[0])]
    for a, b in zip(ctrl[:-1], ctrl[1:]):
        d = math.dist(a, b); n = max(1, int(d / step))
        for t in range(1, n + 1): out.append(tuple(a[k] + (b[k] - a[k]) * t / n for k in range(3)))
    return out

def vertex_fractions(verts, ctrl):
    line = densify(ctrl); m = max(1, len(line) - 1); fr = []
    for v in verts:
        best = 0; bd = 1e9
        for i, p in enumerate(line):
            d = (v[0] - p[0]) ** 2 + (v[1] - p[1]) ** 2 + (v[2] - p[2]) ** 2
            if d < bd: bd = d; best = i
        fr.append(best / m)
    return fr

by_src = {}
for r in splines: by_src.setdefault(r["src"], {})[r["spline"]] = r
originals_path = SPL / "originals.json"
originals = json.load(open(originals_path)) if originals_path.exists() else {}

# drop the output of any earlier run and restore the fused entries, so the script can be re-run after editing the spec
man["meshes"] = [m for m in man["meshes"] if not m.get("split_from")]
have = {m["id"] for m in man["meshes"]}
for oid, rec in originals.items():
    if oid not in have: man["meshes"].append(rec)
entry = {m["id"]: m for m in man["meshes"]}

made = 0; report = []
for src_label, rules in spec.items():
    if src_label.startswith("_"): continue
    srcs = [m for m in man["meshes"] if m["label"] == src_label and m.get("kind") == "CURVE" and m["id"] in by_src]
    if not srcs: print("!! no fused curve named", repr(src_label)); continue
    left = next((m for m in srcs if m["side"] != "r"), srcs[0])
    for src in srcs:
        spl = by_src[src["id"]]
        # the right side must mirror the left spline for spline, or its numbering cannot be trusted
        if src is not left:
            lspl = by_src[left["id"]]
            for k, r in spl.items():
                a = lspl.get(k)
                ok = a is not None and len(a["ctrl"]) == len(r["ctrl"]) and all(math.dist((-p[0], p[1], p[2]), q) < 0.004 for p, q in zip((a["ctrl"][0], a["ctrl"][-1]), (r["ctrl"][0], r["ctrl"][-1])))
                if not ok: print(f"!! {src['id']} spline {k} does not mirror the left side");
        originals.setdefault(src["id"], src)
        pieces = []  # (spline, from, to, label)
        named = {}
        for rule in rules:
            ks = rule["spline"] if isinstance(rule["spline"], list) else [rule["spline"]]
            for k in ks: named.setdefault(k, []).append((rule.get("from", 0.0), rule.get("to", 1.0), rule["label"]))
        for k, r in sorted(spl.items()):
            segs = sorted(named.get(k, [(0.0, 1.0, src_label)]))
            # fill any stretch the spec leaves out with the parent's label
            full = []; cur = 0.0
            for a, b, lab in segs:
                if a > cur + 1e-6: full.append((cur, a, src_label))
                full.append((a, b, lab)); cur = b
            if cur < 1 - 1e-6: full.append((cur, 1.0, src_label))
            verts, idx = read_bin(SPL / f"{r['id']}.bin")
            fr = vertex_fractions(verts, r["ctrl"]) if len(full) > 1 else None
            for si, (a, b, lab) in enumerate(full):
                if fr is None: tri = list(idx)
                else:
                    tri = []
                    for t in range(0, len(idx), 3):
                        f = (fr[idx[t]] + fr[idx[t + 1]] + fr[idx[t + 2]]) / 3
                        if (a <= f < b) or (b >= 1 and f >= b): tri.extend(idx[t:t + 3])
                if not tri: continue
                used = sorted(set(tri)); remap = {v: i for i, v in enumerate(used)}
                oid = f"{r['id']}" + (chr(97 + si) if len(full) > 1 else "")
                rec = write_bin(here / "meshes" / f"{oid}.bin", [verts[v] for v in used], [remap[v] for v in tri])
                rec.update({"id": oid, "name": src["name"], "color": src.get("color"), "label": lab, "side": src["side"], "system": src["system"],
                            "tier": src["tier"], "kind": "CURVE", "polys": rec["tris"], "split_from": src["id"]})
                pieces.append(rec); made += 1
        man["meshes"] = [m for m in man["meshes"] if m["id"] != src["id"]] + pieces
        if src is left: report.append((src_label, sorted({p["label"] for p in pieces})))

json.dump(originals, open(originals_path, "w"))
json.dump(man, open(man_path, "w"))
for lab, parts in report: print(f"{lab}: {len(parts)} labels -> {', '.join(parts)}")
print("pieces written:", made, "| manifest meshes:", len(man["meshes"]))
