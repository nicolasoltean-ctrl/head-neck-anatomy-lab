"""Run inside Blender:
  blender -b Startup.blend --python export_splines.py -- selection.json outdir
Many Z-Anatomy vessels and nerves are ONE curve object holding several splines: the trunk plus its branches.
For every CURVE entry of selection.json with more than one spline, this writes each spline as its own
tube mesh, outdir/<id>-sNN.bin (same HNM1 layout and Y-up conversion as export_meshes.py), and
outdir/splines.json with each spline's centerline so the branches can be identified and named.
"""
import bpy, bmesh, json, sys, struct, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
sel_path, outdir = argv[0], argv[1]
os.makedirs(outdir, exist_ok=True)
selection = [s for s in json.load(open(sel_path)) if s["kind"] == "CURVE"]
out = []

def yup(w): return (w.x, w.z, -w.y)

def write_mesh(obj, oid):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg); me = ev.to_mesh()
    if me is None or len(me.polygons) == 0:
        ev.to_mesh_clear(); return None
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table(); mw = obj.matrix_world
    pts = [yup(mw @ v.co) for v in bm.verts]
    idx = [v.index for f in bm.faces if len(f.verts) == 3 for v in f.verts]
    bm.free(); ev.to_mesh_clear()
    n = len(pts)
    if n == 0 or not idx: return None
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    rng = [max(mx[i] - mn[i], 1e-9) for i in range(3)]
    q = bytearray()
    for p in pts: q += struct.pack("<3h", *[int(round((p[i] - mn[i]) / rng[i] * 65534 - 32767)) for i in range(3)])
    ib = struct.pack("<%d%s" % (len(idx), "I" if n > 65535 else "H"), *idx)
    path = os.path.join(outdir, oid + ".bin")
    with open(path, "wb") as f:
        f.write(b"HNM1"); f.write(struct.pack("<II", n, len(idx))); f.write(struct.pack("<6f", *mn, *mx)); f.write(q); f.write(ib)
    return {"verts": n, "tris": len(idx) // 3, "bbox": [round(v, 4) for v in mn + mx], "bytes": os.path.getsize(path)}

for s in selection:
    o = bpy.data.objects.get(s["name"])
    if o is None or o.type != "CURVE" or len(o.data.splines) < 2: continue
    nspl = len(o.data.splines)
    for k in range(nspl):
        sp = o.data.splines[k]
        mw = o.matrix_world
        if sp.type == "BEZIER": ctrl = [yup(mw @ p.co) for p in sp.bezier_points]
        else: ctrl = [yup(mw @ Vector((p.co.x, p.co.y, p.co.z))) for p in sp.points]
        cd = o.data.copy()
        for i in range(len(cd.splines) - 1, -1, -1):
            if i != k: cd.splines.remove(cd.splines[i])
        tmp = bpy.data.objects.new("tmp_spline", cd); tmp.matrix_world = o.matrix_world.copy()
        bpy.context.scene.collection.objects.link(tmp)
        rec = None
        try: rec = write_mesh(tmp, f"{s['id']}-s{k:02d}")
        except Exception as e: print("ERR", s["name"], k, e)
        bpy.data.objects.remove(tmp); bpy.data.curves.remove(cd)
        if rec:
            rec.update({"id": f"{s['id']}-s{k:02d}", "src": s["id"], "name": s["name"], "spline": k, "nsplines": nspl, "label": s["label"], "side": s["side"],
                        "system": s["system"], "tier": s["tier"], "type": sp.type, "cyclic": bool(sp.use_cyclic_u),
                        "ctrl": [[round(c, 5) for c in p] for p in ctrl]})
            out.append(rec)
json.dump(out, open(os.path.join(outdir, "splines.json"), "w"))
print("SPLINES", len(out), "from", len({r["src"] for r in out}), "curves")
