"""Run inside Blender:
  blender -b Startup.blend --python export_meshes.py -- selection.json outdir [max_tris]
selection.json: [{"name": "<blender object name>", "id": "<output id>"}, ...]
Writes outdir/<id>.bin (compact quantized mesh) and outdir/manifest.json.

Binary layout (little endian):
  magic "HNM1" (4 bytes) | uint32 nVerts | uint32 nIdx | float32 min[3] | float32 max[3]
  int16 pos[nVerts*3] (quantized into bbox, -32767..32767) | uint16 or uint32 idx[nIdx] (uint32 if nVerts > 65535)
Coordinates are converted from Blender Z-up to Y-up (x, z, -y) in world space, units preserved.
"""
import bpy, bmesh, json, sys, struct, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
sel_path, outdir = argv[0], argv[1]
max_tris = int(argv[2]) if len(argv) > 2 else 40000
os.makedirs(outdir, exist_ok=True)
selection = json.load(open(sel_path))
manifest = []
depsgraph = bpy.context.evaluated_depsgraph_get()

def export_one(o, oid):
    ev = o.evaluated_get(depsgraph)
    me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    ntris = len(bm.faces)
    if ntris > max_tris:
        # decimate on a temporary mesh copy
        tmp = bpy.data.meshes.new("tmp_dec"); bm.to_mesh(tmp); bm.free()
        tobj = bpy.data.objects.new("tmp_dec_obj", tmp); bpy.context.scene.collection.objects.link(tobj)
        mod = tobj.modifiers.new("dec", "DECIMATE"); mod.ratio = max_tris / ntris; mod.use_collapse_triangulate = True
        dg = bpy.context.evaluated_depsgraph_get(); tev = tobj.evaluated_get(dg); dme = tev.to_mesh()
        bm = bmesh.new(); bm.from_mesh(dme); bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tev.to_mesh_clear(); bpy.data.objects.remove(tobj); bpy.data.meshes.remove(tmp)
    bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
    mw = o.matrix_world
    pts = []
    for v in bm.verts:
        w = mw @ v.co
        pts.append((w.x, w.z, -w.y))  # Z-up -> Y-up
    idx = []
    for f in bm.faces:
        if len(f.verts) != 3: continue
        idx.extend(v.index for v in f.verts)
    n = len(pts)
    if n == 0 or not idx:
        bm.free(); ev.to_mesh_clear(); return None
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    rng = [max(mx[i] - mn[i], 1e-9) for i in range(3)]
    q = bytearray()
    for p in pts:
        q += struct.pack("<3h", *[int(round((p[i] - mn[i]) / rng[i] * 65534 - 32767)) for i in range(3)])
    wide = n > 65535
    ib = struct.pack("<%d%s" % (len(idx), "I" if wide else "H"), *idx)
    path = os.path.join(outdir, oid + ".bin")
    with open(path, "wb") as f:
        f.write(b"HNM1"); f.write(struct.pack("<II", n, len(idx))); f.write(struct.pack("<6f", *mn, *mx)); f.write(q); f.write(ib)
    bm.free(); ev.to_mesh_clear()
    col = None
    for m in me.materials if False else o.data.materials:
        if m is None: continue
        try:
            if m.use_nodes and m.node_tree:
                for nd in m.node_tree.nodes:
                    if nd.type == "BSDF_PRINCIPLED": col = [round(x, 3) for x in nd.inputs["Base Color"].default_value[:3]]; break
            if col is None: col = [round(x, 3) for x in m.diffuse_color[:3]]
        except Exception: pass
        if col: break
    return {"id": oid, "name": o.name, "verts": n, "tris": len(idx) // 3, "bbox": [round(v, 4) for v in mn + mx], "bytes": os.path.getsize(path), "color": col}

done = 0; missing = []
for s in selection:
    o = bpy.data.objects.get(s["name"])
    if o is None or o.type not in ("MESH", "CURVE"): missing.append(s["name"]); continue
    try:
        rec = export_one(o, s["id"])
    except Exception as e:
        print("ERR", s["name"], e); missing.append(s["name"]); continue
    if rec:
        rec.update({k: v for k, v in s.items() if k not in ("name", "id")})
        manifest.append(rec); done += 1
json.dump({"meshes": manifest, "missing": missing}, open(os.path.join(outdir, "manifest.json"), "w"))
print("EXPORTED", done, "missing", len(missing), "total bytes", sum(m["bytes"] for m in manifest))
