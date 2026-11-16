import json, struct, sys, numpy as np
S = sys.argv[1]
man = json.load(open("meshes/manifest.json"))["meshes"]
def load(mid):
    b = open(f"meshes/{mid}.bin", "rb").read()
    nV, nI = struct.unpack_from("<II", b, 4); mn = np.array(struct.unpack_from("<3f", b, 12)); mx = np.array(struct.unpack_from("<3f", b, 24))
    q = np.frombuffer(b, dtype="<i2", count=nV*3, offset=36).reshape(-1,3).astype(np.float64)
    v = mn + (q + 32767) / 65534 * (mx - mn)
    idx = np.frombuffer(b, dtype="<u4" if nV > 65535 else "<u2", count=nI, offset=36 + nV*6).reshape(-1,3)
    return v, idx
box = np.array([[-0.03, 1.44, -0.01], [0.03, 1.61, 0.115]])
pts = []; owner = []; names = []
for m in man:
    if m["system"] not in ("viscera", "bone", "muscle", "lymph"): continue
    bb = m["bbox"]
    if bb[3] < box[0][0] or bb[0] > box[1][0] or bb[4] < box[0][1] or bb[1] > box[1][1] or bb[5] < box[0][2] or bb[2] > box[1][2]: continue
    v, idx = load(m["id"]); a, b, c = v[idx[:,0]], v[idx[:,1]], v[idx[:,2]]
    P = np.concatenate([v, (a+b)/2, (b+c)/2, (c+a)/2, (a+b+c)/3])
    P = P[np.all((P > box[0]) & (P < box[1]), axis=1)]
    if m["label"] in ("Soft palate", "Uvula of palate"): P = P + np.array([0, -0.001, 0.004])
    if len(P): pts.append(P); owner += [len(names)] * len(P); names.append(m["label"])
P = np.concatenate(pts); owner = np.array(owner); print("cloud", len(P), "points from", len(names), "meshes")
W = np.array([[5,1558,103],[4.2,1560,90],[4.5,1561,78],[3.8,1559,68],[3.6,1562,60],[4.5,1563,52],[5,1562,45],[5,1561,36],[4,1560,26],[3,1558,18.5],[3.5,1552,16],[3,1546,15.5],[2,1538,16.5],[1,1528,17],[0,1518,17],[0,1510,17],[0,1503,15.5]], dtype=float) / 1000
def resample(W, step=0.0015):
    seg = np.linalg.norm(np.diff(W, axis=0), axis=1); s = np.concatenate([[0], np.cumsum(seg)]); n = int(s[-1] / step) + 1
    t = np.linspace(0, s[-1], n); return np.stack([np.interp(t, s, W[:, k]) for k in range(3)], axis=1)
base = resample(W, 0.001); path = base.copy()
for it in range(40):
    new = path.copy()
    for j in range(1, len(path) - 1):
        p = path[j]; tan = path[j+1] - path[j-1]; tan /= np.linalg.norm(tan) + 1e-12
        d = np.linalg.norm(P - p, axis=1); near = d < 0.007
        if near.any():
            q = P[near]; w = 1.0 / np.maximum(d[near], 3e-4) ** 3; push = ((p - q) * w[:, None]).sum(0); push -= tan * push.dot(tan); n = np.linalg.norm(push)
            if n > 0: new[j] = p + push / n * 0.00012
    new[1:-1] = 0.15 * new[:-2] + 0.7 * new[1:-1] + 0.15 * new[2:]
    off = new - base; r = np.linalg.norm(off, axis=1, keepdims=True); new = base + off * np.minimum(1, 0.0015 / np.maximum(r, 1e-9)); path = new
cl = []; nearest = []
for p in path:
    d = np.linalg.norm(P - p, axis=1); i = d.argmin(); cl.append(d[i]); nearest.append(names[owner[i]])
cl = np.array(cl); L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(path, axis=0), axis=1))])
print(f"path {len(path)} pts, length {L[-1]*1000:.0f} mm, clearance min {cl.min()*1000:.1f} mm, median {np.median(cl)*1000:.1f} mm")
for j in range(0, len(path), max(1, len(path)//24)):
    p = path[j]; print(f"  s={L[j]*1000:5.0f}mm [{p[0]*1000:5.1f},{p[1]*1000:7.1f},{p[2]*1000:6.1f}] clear {cl[j]*1000:4.1f}mm near {nearest[j]}")
json.dump({"path": [[round(float(x), 5) for x in p] for p in path], "len_mm": round(float(L[-1]*1000), 1), "clear_mm": [round(float(c*1000), 2) for c in cl], "nearest": nearest}, open(f"{S}/scope_path.json", "w"))
