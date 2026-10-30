"""Run inside Blender: blender -b Startup.blend --python inspect_blend.py -- out.json
Dumps every object with its collection chain, parent, vertex count, world bbox, material color.
"""
import bpy, json, sys
from mathutils import Vector

out = sys.argv[sys.argv.index("--") + 1]

# collection parent map
parents = {}
def walk(col, chain):
    for ch in col.children:
        parents[ch.name] = chain + [ch.name]
        walk(ch, chain + [ch.name])
walk(bpy.context.scene.collection, [])

objs = []
for o in bpy.data.objects:
    rec = {
        "name": o.name, "type": o.type, "parent": o.parent.name if o.parent else None,
        "collections": [parents.get(c.name, [c.name]) for c in o.users_collection],
        "hide_viewport": o.hide_viewport, "hide_render": o.hide_render,
    }
    if o.type == "MESH":
        me = o.data
        rec["verts"] = len(me.vertices); rec["polys"] = len(me.polygons)
        try:
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            xs = [v.x for v in bb]; ys = [v.y for v in bb]; zs = [v.z for v in bb]
            rec["bbox"] = [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4), round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)]
        except Exception as e:
            rec["bbox"] = None
        mats = []
        for m in me.materials:
            if m is None: continue
            col = None
            try:
                if m.use_nodes and m.node_tree:
                    for n in m.node_tree.nodes:
                        if n.type == "BSDF_PRINCIPLED":
                            col = [round(x, 3) for x in n.inputs["Base Color"].default_value[:4]]; break
                if col is None: col = [round(x, 3) for x in m.diffuse_color[:4]]
            except Exception: pass
            mats.append({"name": m.name, "color": col})
        rec["materials"] = mats
        # custom props (Z-Anatomy stores definitions / TA ids sometimes)
        props = {k: (str(o[k])[:200]) for k in o.keys() if not k.startswith("_")}
        if props: rec["props"] = props
    objs.append(rec)

cols = {name: chain for name, chain in parents.items()}
json.dump({"blender": bpy.app.version_string, "objects": objs, "collections": cols,
           "scene": bpy.context.scene.name, "unit": bpy.context.scene.unit_settings.length_unit,
           "scale": bpy.context.scene.unit_settings.scale_length}, open(out, "w"))
print("WROTE", out, len(objs), "objects", len(cols), "collections")
