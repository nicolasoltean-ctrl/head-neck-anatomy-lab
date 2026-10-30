import bpy, json, sys
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
parents = {}
def walk(col, chain):
    for ch in col.children:
        parents[ch.name] = chain + [ch.name]; walk(ch, chain + [ch.name])
walk(bpy.context.scene.collection, [])
res = []
dg = bpy.context.evaluated_depsgraph_get()
for o in bpy.data.objects:
    if o.type != "CURVE": continue
    try:
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        bbox = [round(min(v.x for v in bb),4), round(min(v.y for v in bb),4), round(min(v.z for v in bb),4), round(max(v.x for v in bb),4), round(max(v.y for v in bb),4), round(max(v.z for v in bb),4)]
    except Exception: bbox = None
    c = o.data
    try:
        ev = o.evaluated_get(dg); me = ev.to_mesh(); nv = len(me.vertices) if me else 0; npoly = len(me.polygons) if me else 0; ev.to_mesh_clear()
    except Exception as e: nv, npoly = -1, -1
    res.append({"name": o.name, "collections": [parents.get(x.name, [x.name]) for x in o.users_collection], "bbox": bbox,
                "bevel_depth": round(c.bevel_depth, 5), "bevel_object": c.bevel_object.name if c.bevel_object else None, "splines": len(c.splines),
                "mesh_verts": nv, "mesh_polys": npoly, "mats": [m.name for m in c.materials if m]})
json.dump(res, open(out, "w")); print("WROTE", len(res))
