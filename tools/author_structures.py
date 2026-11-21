"""Add the structures that Z-Anatomy does not have for thyroid surgery, and split the thyroid gland into its parts.

  /Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 tools/author_structures.py [--extra DIR]

(any Python with numpy will do). Run from the project root, after tools/split_branches.py and before build3d.py. Re-runnable: it
removes the entries of its own earlier runs from meshes/manifest.json first.

What it writes into meshes/ (and meshes/manifest.json, flagged "authored": "drawn" (invented course; the viewer says so) or "source" (cut or exported from the source model)):
  * recurrent laryngeal nerve (both sides, the right one looping under the subclavian artery), superior laryngeal nerve with its
    internal and external branches, superior thyroid artery with its branches, middle thyroid vein, inferior thyroid veins,
    the terminal branches of the inferior thyroid artery, ligament of Berry, tubercle of Zuckerkandl;
  * the thyroid gland cut into right lobe, left lobe, isthmus and pyramidal lobe (the source has one shell);
  * oesophagus and thymus, if --extra points at a folder with oesophagus.bin, thymus-lobe-l.bin, thymus-lobe-r.bin exported by
    tools/export_meshes.py (the source model has them, but they were outside the head-and-neck selection).
The authored tubes are drawn through waypoints that were placed against the model's own vessels, cartilages and airway, following
the course in Netter and in the Open Access Atlas thyroidectomy chapter. They are schematic: their routes are right, their exact
millimetres are not measurements.
"""
import json, math, pathlib, struct, sys
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent.parent
M = HERE / "meshes"

# ---------------------------------------------------------------- mesh files (HNM1, see export_meshes.py)
def read_bin(path):
    b = open(path, "rb").read(); nV, nI = struct.unpack_from("<II", b, 4)
    mn = np.array(struct.unpack_from("<3f", b, 12)); mx = np.array(struct.unpack_from("<3f", b, 24))
    q = np.frombuffer(b, dtype="<i2", count=nV * 3, offset=36).reshape(-1, 3).astype(float)
    v = mn + (q + 32767) / 65534 * (mx - mn)
    idx = np.frombuffer(b, dtype="<u4" if nV > 65535 else "<u2", count=nI, offset=36 + nV * 6).reshape(-1, 3).astype(np.int64)
    return v * 1000.0, idx  # millimetres

def write_bin(path, v_mm, idx):
    v = np.asarray(v_mm, float) / 1000.0; idx = np.asarray(idx, np.int64).reshape(-1)
    n = len(v); mn = v.min(0); mx = v.max(0); rng = np.maximum(mx - mn, 1e-9)
    q = np.round((v - mn) / rng * 65534 - 32767).astype("<i2")
    with open(path, "wb") as f:
        f.write(b"HNM1"); f.write(struct.pack("<II", n, len(idx))); f.write(struct.pack("<6f", *mn, *mx)); f.write(q.tobytes())
        f.write(idx.astype("<u4" if n > 65535 else "<u2").tobytes())
    return {"verts": n, "tris": len(idx) // 3, "bbox": [round(float(x), 4) for x in list(mn) + list(mx)], "bytes": pathlib.Path(path).stat().st_size}

def normals(v, idx):
    n = np.zeros_like(v); a, b, c = v[idx[:, 0]], v[idx[:, 1]], v[idx[:, 2]]; fn = np.cross(b - a, c - a)
    for k in range(3): np.add.at(n, idx[:, k], fn)
    l = np.linalg.norm(n, axis=1, keepdims=True); return n / np.maximum(l, 1e-12)

class Surf:
    """Vertices and normals of an existing mesh, for placing things on it."""
    def __init__(self, name, path=None):
        self.v, self.i = read_bin(path or M / f"{name}.bin"); self.n = normals(self.v, self.i)
    def near(self, p, inset=0.0):
        k = int(np.argmin(((self.v - np.asarray(p, float)) ** 2).sum(1))); return self.v[k] - self.n[k] * inset
    def dist(self, pts):
        return np.sqrt(((pts[:, None, :] - self.v[None, ::3, :]) ** 2).sum(2)).min(1)

# ---------------------------------------------------------------- tubes
def spline(points, step=0.6):
    P = np.array(points, float)
    if len(P) == 2: P = np.array([P[0], (P[0] * 2 + P[1]) / 3, (P[0] + P[1] * 2) / 3, P[1]])
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1:i + 3]; n = max(2, int(np.linalg.norm(p2 - p1) / step))
        for t in np.linspace(0, 1, n, endpoint=False):
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1]); return np.array(out)

def tube(points, radii, sides=10, step=0.6, flat=None, round_end=True):
    """Tube through waypoints (mm). radii: [(u, r)] along the length, u 0..1. flat=(wide, thin): an elliptical band, wide side vertical."""
    line = spline(points, step); n = len(line)
    seg = np.linalg.norm(np.diff(line, axis=0), axis=1); u = np.concatenate([[0], np.cumsum(seg)]); u /= u[-1]
    rr = np.interp(u, [a for a, _ in radii], [b for _, b in radii])
    T = np.gradient(line, axis=0); T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    ref = np.array([0.0, 1.0, 0.0]) if flat else np.array([0.0, 0.0, 1.0])
    a = ref - (ref @ T[0]) * T[0]
    if np.linalg.norm(a) < 1e-3: a = np.array([1.0, 0, 0]) - T[0][0] * T[0]
    a /= np.linalg.norm(a); verts = []
    for k in range(n):
        a = a - (a @ T[k]) * T[k]; a /= max(np.linalg.norm(a), 1e-12)  # carry the frame along without twisting
        b = np.cross(T[k], a); wa, wb = flat if flat else (1.0, 1.0)
        for s in range(sides):
            t = 2 * math.pi * s / sides; verts.append(line[k] + rr[k] * (math.cos(t) * a * wa + math.sin(t) * b * wb))
    idx = []
    for k in range(n - 1):
        for s in range(sides):
            s2 = (s + 1) % sides; p, q, r, t = k * sides + s, k * sides + s2, (k + 1) * sides + s, (k + 1) * sides + s2
            idx += [p, q, r, q, t, r]
    for end, first in ((0, True), (n - 1, False)):  # close the ends
        c = len(verts); verts.append(line[end] + (-T[end] if first else T[end]) * (rr[end] * 0.6 if round_end else 0))
        base = end * sides
        for s in range(sides):
            s2 = (s + 1) % sides; idx += [c, base + s2, base + s] if first else [c, base + s, base + s2]
    return np.array(verts), np.array(idx)

def blob(center, radii, rings=8, sides=14, tilt=None):
    verts = []; idx = []
    for i in range(rings + 1):
        th = math.pi * i / rings
        for s in range(sides):
            ph = 2 * math.pi * s / sides
            verts.append([radii[0] * math.sin(th) * math.cos(ph), radii[1] * math.cos(th), radii[2] * math.sin(th) * math.sin(ph)])
    for i in range(rings):
        for s in range(sides):
            s2 = (s + 1) % sides; p, q, r, t = i * sides + s, i * sides + s2, (i + 1) * sides + s, (i + 1) * sides + s2
            idx += [p, r, q, q, r, t]
    return np.array(verts) + np.asarray(center, float), np.array(idx)

mir = lambda pts: [[-x, y, z] for x, y, z in pts]

# ---------------------------------------------------------------- the structures (millimetres, patient LEFT = +x, anterior = +z, up = +y)
def build():
    gland = Surf("thyroid-gland"); tr = Surf("trachea"); cr = Surf("cricoid-cartilage")
    out = []  # (id, label, side, system, tier, verts, idx)
    def add(oid, label, side, system, tier, vi, kind="CURVE"): out.append((oid, label, side, system, tier, vi[0], vi[1], kind))
    nerve = lambda u0, u1: [(0, u0), (0.12, u0 * 1.15), (0.85, u1 * 1.1), (1, u1 * 0.6)]

    # recurrent laryngeal nerve: from the vagus below the arch (left) / around the subclavian artery (right), up the tracheo-oesophageal
    # groove, behind the cricothyroid joint, to enter the larynx under the inferior constrictor
    rln_up = [(11.2, 1368, -16.6), (10.9, 1390, -14.8), (10.9, 1410, -8.8), (11.0, 1430, -3.4), (10.8, 1448, 1.0), (10.5, 1458, 2.4), (10.0, 1464, 3.6), (9.2, 1469, 4.8)]
    rln_l = [(10.7, 1355.5, -13.4)] + rln_up
    rln_r = [(-17.0, 1412.5, -3.4), (-15.6, 1406.0, -1.4), (-12.8, 1403.6, -3.4), (-10.8, 1408.5, -6.8), (-10.9, 1418, -5.6)] + mir(rln_up[3:])
    add("recurrent-laryngeal-nerve-l", "Recurrent laryngeal nerve", "l", "nerve", 3, tube(rln_l, nerve(0.55, 0.45)))
    add("recurrent-laryngeal-nerve-r", "Recurrent laryngeal nerve", "r", "nerve", 3, tube(rln_r, nerve(0.55, 0.45)))

    # superior laryngeal nerve from the vagus; internal branch to the thyrohyoid membrane, external branch down the inferior constrictor
    sln = [(25.6, 1514, 2.6), (22.6, 1508.5, 3.4), (20.2, 1504.2, 4.0)]
    iln = [(20.2, 1504.2, 4.0), (17.4, 1502.4, 8.4), (15.2, 1500.0, 13.6), (14.2, 1497.2, 19.8), (13.8, 1495.0, 23.6)]
    eln = [(20.2, 1504.2, 4.0), (17.6, 1497.0, 4.9), (15.4, 1488.6, 6.2), (13.8, 1480.4, 8.0), (12.4, 1473.0, 10.4), (11.0, 1467.4, 13.0)]
    for sd, f in (("l", lambda p: p), ("r", mir)):
        add(f"superior-laryngeal-nerve-{sd}", "Superior laryngeal nerve", sd, "nerve", 3, tube(f(sln), [(0, 0.45), (1, 0.4)]))
        add(f"internal-laryngeal-nerve-{sd}", "Internal laryngeal nerve", sd, "nerve", 3, tube(f(iln), [(0, 0.4), (1, 0.25)]))
        add(f"external-laryngeal-nerve-{sd}", "External laryngeal nerve", sd, "nerve", 3, tube(f(eln), [(0, 0.35), (1, 0.18)]))

    # superior thyroid artery: first branch of the external carotid, to the upper pole, then anterior and posterior glandular branches on the surface
    sta = [(31.0, 1488.4, 1.2), (29.6, 1488.4, 4.6), (27.2, 1487.2, 8.0), (24.0, 1485.6, 10.2)]
    def on(gl, pts, lift=0.5): return [gl.near(p) + gl.n[int(np.argmin(((gl.v - gl.near(p)) ** 2).sum(1)))] * lift for p in pts]
    sta_ant = [sta[-1]] + on(gland, [(22.0, 1481, 16.5), (19.0, 1474, 23.5), (13.0, 1466, 28.5)])
    sta_post = [sta[-1]] + on(gland, [(22.5, 1481, 2.0), (19.5, 1474, -2.0), (16.0, 1468, -3.8)])
    sta_med = [sta[-1]] + on(gland, [(21.5, 1485, 8.0), (13.0, 1486, 8.5)])
    for sd, f in (("l", lambda p: p), ("r", mir)):
        add(f"superior-thyroid-artery-{sd}", "Superior thyroid artery", sd, "artery", 3, tube(f(sta), [(0, 1.05), (1, 0.8)]))
        add(f"superior-thyroid-artery-{sd}-ant", "Superior thyroid artery", sd, "artery", 3, tube(f(sta_ant), [(0, 0.8), (1, 0.3)]))
        add(f"superior-thyroid-artery-{sd}-post", "Superior thyroid artery", sd, "artery", 3, tube(f(sta_post), [(0, 0.75), (1, 0.3)]))

    # inferior thyroid artery: the source stops lateral to the carotid sheath; carry it behind the sheath to the back of the lobe,
    # with a lower branch that crosses in front of the recurrent nerve
    ita = [(32.8, 1459.7, 5.2), (31.4, 1459.0, -1.4), (28.4, 1458.6, -5.8), (23.6, 1458.8, -6.2), (19.0, 1459.2, -4.8), (16.6, 1460.0, -3.4)]
    ita_low = [(19.0, 1459.2, -4.8), (15.2, 1455.5, -2.6), (12.2, 1453.0, 2.0), (11.0, 1452.2, 5.8), (9.0, 1451.5, 9.2)]
    ita_up = [(19.0, 1459.2, -4.8), (18.2, 1465.5, -5.2), (17.4, 1471.5, -4.8)]
    for sd, f in (("l", lambda p: p), ("r", mir)):
        add(f"inferior-thyroid-artery-{sd}-ext", "Inferior thyroid artery", sd, "artery", 3, tube(f(ita), [(0, 0.95), (1, 0.8)]))
        add(f"inferior-thyroid-artery-{sd}-low", "Inferior thyroid artery", sd, "artery", 3, tube(f(ita_low), [(0, 0.7), (1, 0.28)]))
        add(f"inferior-thyroid-artery-{sd}-up", "Inferior thyroid artery", sd, "artery", 3, tube(f(ita_up), [(0, 0.6), (1, 0.28)]))

    # middle thyroid vein: lateral surface of the lobe straight to the internal jugular vein
    mtv = on(gland, [(19.6, 1468, 11.5)], 0.8) + [(22.0, 1468.8, 11.6), (24.4, 1469.2, 11.6), (26.0, 1469.4, 11.6)]
    # inferior thyroid veins: down the front of the trachea to the jugulo-subclavian junction (the brachiocephalic veins are not in the model)
    itv1 = on(gland, [(9.0, 1456.5, 22.0)], 0.8) + [(10.0, 1446, 19.8), (12.8, 1434, 17.8), (17.4, 1423, 17.8), (21.6, 1416.2, 18.0), (24.2, 1414.4, 18.4)]
    itv2 = on(gland, [(4.0, 1457.5, 22.5)], 0.8) + [(5.8, 1446, 20.0), (8.8, 1436, 18.0), (12.6, 1431.2, 17.6)]
    itv_r_end = [(-21.4, 1408.0, 18.0), (-23.6, 1406.6, 17.9)]
    add("middle-thyroid-vein-l", "Middle thyroid vein", "l", "vein", 3, tube(mtv, [(0, 1.5), (1, 1.8)]))
    add("middle-thyroid-vein-r", "Middle thyroid vein", "r", "vein", 3, tube(mir(mtv), [(0, 1.5), (1, 1.8)]))
    add("inferior-thyroid-veins-l-a", "Inferior thyroid veins", "l", "vein", 3, tube(itv1, [(0, 1.1), (1, 1.5)]))
    add("inferior-thyroid-veins-l-b", "Inferior thyroid veins", "l", "vein", 3, tube(itv2, [(0, 0.95), (1, 1.1)]))
    add("inferior-thyroid-veins-r-a", "Inferior thyroid veins", "r", "vein", 3, tube(mir(itv1[:5]) + itv_r_end, [(0, 1.1), (1, 1.5)]))
    add("inferior-thyroid-veins-r-b", "Inferior thyroid veins", "r", "vein", 3, tube(mir(itv2), [(0, 0.95), (1, 1.1)]))

    # ligament of Berry: a short band from the back of the lobe to the side of the cricoid, with the nerve just behind it
    for sd, s in (("l", 1), ("r", -1)):
        a = gland.near([s * 16.8, 1462.5, 4.0], 0.4); b = cr.near([s * 11.0, 1463.0, 4.6], 0.4)
        mid = (a + b) / 2 + np.array([0, 0, -0.3])
        add(f"ligament-of-berry-{sd}", "Ligament of Berry", sd, "viscera", 4, tube([a, mid, b], [(0, 1.0), (0.5, 0.8), (1, 1.0)], flat=(3.2, 0.7)), "MESH")
        c = gland.near([s * 19.4, 1472.0, -3.0]); k = int(np.argmin(((gland.v - c) ** 2).sum(1)))
        add(f"tubercle-of-zuckerkandl-{sd}", "Tubercle of Zuckerkandl", sd, "viscera", 4, blob(gland.v[k] + gland.n[k] * 0.4, (1.9, 2.4, 1.7)), "MESH")
    return out, gland

# ---------------------------------------------------------------- the gland in parts
def split_gland():
    v, idx = read_bin(M / "thyroid-gland.bin"); c = v[idx].mean(1); part = np.zeros(len(idx), int)  # 0 left lobe, 1 right lobe, 2 isthmus, 3 pyramidal lobe
    part[c[:, 0] < 0] = 1
    isth = (np.abs(c[:, 0]) < 7.5) & (c[:, 1] <= 1466) & (c[:, 2] > 16); pyr = (np.abs(c[:, 0]) < 5.0) & (c[:, 1] > 1466) & (c[:, 2] > 24)
    part[isth] = 2; part[pyr] = 3
    res = {}
    for k, (name, label, side) in enumerate([("thyroid-gland-l", "Thyroid gland", "l"), ("thyroid-gland-r", "Thyroid gland", "r"), ("thyroid-isthmus", "Isthmus of thyroid gland", "m"), ("thyroid-pyramidal-lobe", "Pyramidal lobe of thyroid gland", "m")]):
        tri = idx[part == k]
        if not len(tri): continue
        used = np.unique(tri); remap = -np.ones(len(v), int); remap[used] = np.arange(len(used))
        res[name] = (label, side, v[used], remap[tri])
    return res

# ---------------------------------------------------------------- driver
def main():
    extra = pathlib.Path(sys.argv[sys.argv.index("--extra") + 1]) if "--extra" in sys.argv else None
    man_path = M / "manifest.json"; man = json.load(open(man_path)); orig_path = M / "authored_originals.json"
    originals = json.load(open(orig_path)) if orig_path.exists() else {}
    man["meshes"] = [m for m in man["meshes"] if not m.get("authored")]
    have = {m["id"] for m in man["meshes"]}
    for oid, rec in originals.items():  # undo the gland split of an earlier run
        if oid not in have: man["meshes"].append(rec)
    gl = next((m for m in man["meshes"] if m["id"] == "thyroid-gland"), None)
    if gl: originals["thyroid-gland"] = gl
    json.dump(originals, open(orig_path, "w"))
    new = []
    def put(oid, label, side, system, tier, v, i, kind, drawn=False):
        rec = write_bin(M / f"{oid}.bin", v, i)
        rec.update({"id": oid, "name": label, "color": None, "label": label, "side": side, "system": system, "tier": tier, "kind": kind, "polys": rec["tris"], "authored": "drawn" if drawn else "source"}); new.append(rec)
    out, _ = build()
    for o in out: put(*o, drawn=True)
    for oid, (label, side, v, i) in split_gland().items(): put(oid, label, side, "viscera", 4, v, i, "MESH")
    man["meshes"] = [m for m in man["meshes"] if m["id"] != "thyroid-gland"]
    if extra:  # oesophagus and thymus, exported from the source model; keep the part from the thoracic inlet upwards
        for oid, label, side in (("oesophagus", "Oesophagus", "m"), ("thymus-lobe-l", "Thymus", "l"), ("thymus-lobe-r", "Thymus", "r")):
            p = extra / f"{oid}.bin"
            if not p.exists(): print("missing", p); continue
            v, i = read_bin(p); keep = i[v[i][:, :, 1].mean(1) >= 1352.0]
            used = np.unique(keep); remap = -np.ones(len(v), int); remap[used] = np.arange(len(used))
            put(oid, label, side, "viscera", 4, v[used], remap[keep], "CURVE" if oid == "oesophagus" else "MESH")
    else:
        for oid in ("oesophagus", "thymus-lobe-l", "thymus-lobe-r"):
            if (M / f"{oid}.bin").exists() and oid not in {m["id"] for m in man["meshes"]}: print("note:", oid, "is on disk but not in the manifest; pass --extra")
    man["meshes"] += new; json.dump(man, open(man_path, "w"))
    print("authored", len(new), "meshes;", sum(1 for m in new if m["system"] in ("nerve", "artery", "vein")), "tubes")

if __name__ == "__main__":
    main()
