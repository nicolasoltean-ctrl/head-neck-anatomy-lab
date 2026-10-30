import json, re, sys, collections
S = sys.argv[1]
meshes = json.load(open(f"{S}/zanatomy_objects.json"))["objects"]
curves = json.load(open(f"{S}/zanatomy_curves.json"))
objs = [dict(o, kind="MESH") for o in meshes if o["type"] == "MESH" and o.get("bbox") and o.get("verts", 0) > 2] + [dict(o, kind="CURVE") for o in curves if o["bbox"] and o["mesh_polys"] > 0]

EXCL = re.compile(r"lung|bronch|aorta|vena cava|azygos|intercostal|humer|axilla|brachial (artery|vein)|radial nerve|ulnar nerve|median nerve|musculocutaneous|thoraco|pectoral|deltoid|teres|infraspinatus|supraspinatus|subscapular|biceps|triceps|coracobrachial|serratus|rhomboid|latissimus|scapula|glenoid|glenohumeral|acromi|coraco|clavipectoral|cephalic vein|circumflex|subclavius|thymus|pleura|oesophag|esophag|thoracic (aorta|vert|duct)|vertebra T[2-9]|disc T|pulposus T|rib$|rib\b|costal|levatores|iliocostalis|longissimus thoracis|spinalis thoracis|semispinalis thoracis|multifidus thoracis|interspinales thoracis|rotatores|investing abdominal|cross section|reference|median line|planes?$|line$|\.g$|^\?|abduction|adduction|rotation|circumduction|caudal|cranial$|frontal$|occipital$|supreme intercostal|posterior intercostal|superior intercostal|hemi-azygos|segmental|central canal|medulla-path|zonular fibers-curve|ciliary body-curve|brachial plexus|antebrachial|cutaneous nerve|thoracodorsal|long thoracic|dorsal scapular|suprascapular|lateral thoracic|subscapular|axillary|hairs|eyelashes|eyebrow|ligamentum arteriosum|parasternal|prepericardial|tracheobronchial|intrapulmonary|juxta-oesophageal|brachiocephalic nodes|brachial nodes|infraclavicular|intercostal nodes|posterior axillary|paratracheal thoracic|mediastinal|interscapular|scapular region|pectoral region|presternal|infraclavicular fossa|deltopectoral|lateral region of thorax|vertebral region|deltoid region|mamillary|midclavicular|sternal line|parasternal line|paravertebral|nerve to subclavius|subclavian nerve|first rib|second rib|third rib|fourth rib|fifth rib|manubrium|sternum|costoclavicular|interclavicular|sternoclavicular|conoid|trapezoid ligament|supraspinous|interspinous|intertransverse|ligamenta flava|longitudinal ligament|nuchal", re.I)
BRAIN = re.compile(r"gyrus|gyri|sulcus|sulci|lobule|vermis|cerebell|cerebr|thalam|hippocamp|amygdal|caudate|putamen|pallidus|lentiform|fornix|commissure|ventricle|aqueduct|colliculus|pons|medulla|midbrain|peduncle|nucleus|tract|fasciculus|olive|pyramid|corpus callosum|septum|stria|habenula|mamillary body|hypothalamus|geniculate|capsule|white matter|choroid|falx|tentorium|cuneus|precuneus|insula|lat_fis|temporal plane|temporal pole|occipital pole|culmen|declive|folium|tuber|uvula of vermis|nodule|flocculus|lingula|pyramis|tonsil of cerebellum|central lobule|biventral|semilunar|quadrangular|wing of central|spinal cord|spinal dura|horn of spinal|intermediate substance|reticular|spinotectal|dura|pituitary|hypophysis|pineal|optic chiasm|optic tract|interpeduncular|substantia|red nucleus|olfactory bulb", re.I)
EYE_EAR = re.compile(r"eyeball|cornea|iris|lens|retina|sclera|vitreous|zonular|lacrimal|nasolacrimal|cochlea|vestibule|tympanic|auditory tube|tarsus|conjunctiva|meridians|equator|axis of eyeball|segment of eyeball|chamber|suspensory ligament of eyeball|ampulla", re.I)

def system_of(o):
    n = o["name"]; col = o["collections"][0][0] if o["collections"] else ""
    nl = n.lower()
    if col.startswith("9:"): return "skin"
    if col.startswith("1:") or col.startswith("3:"): return "bone"
    if col.startswith("2:"): return "bone"
    if col.startswith("4:"): return "muscle"
    if col.startswith("6:"): return "lymph"
    if col.startswith("5:"):
        return "vein" if re.search(r"vein|sinus|venous|plexus", nl) else "artery"
    if col.startswith("7:"):
        if o["kind"] == "CURVE" or re.search(r"nerve|chorda|plexus|trunk|ganglion|sympathetic|root of spinal", nl): 
            if BRAIN.search(nl) and not re.search(r"\bnerve\b", nl): return "cns"
            return "nerve"
        if EYE_EAR.search(nl): return "viscera"
        return "cns"
    if col.startswith("8:"): return "viscera"
    return None

SUPERFICIAL_MUSCLE = re.compile(r"platysma|epicranial|frontalis|occipitalis|temporoparietalis|orbicularis|corrugator|procerus|nasalis|depressor|levator labii|levator anguli|levator nasolabialis|zygomaticus|risorius|mentalis|bucinator|buccinator|superficial investing|superficial layer of temporal fascia|masseteric fascia|tarsus", re.I)
def tier_of(sys_, o):
    nl = o["name"].lower()
    if sys_ == "skin": return 0
    if sys_ == "muscle": return 1 if SUPERFICIAL_MUSCLE.search(nl) else 2
    if sys_ in ("vein",): return 3
    if sys_ in ("artery",): return 3
    if sys_ in ("nerve", "lymph"): return 3
    if sys_ == "viscera": return 4
    if sys_ == "bone": return 5
    if sys_ == "cns": return 6
    return 4

sel = []; skipped = collections.Counter(); seen = set()
for o in objs:
    b = o["bbox"]; n = o["name"]
    if b[5] < 1.36 or b[2] < 1.30: skipped["below-neck"] += 1; continue
    if min(abs(b[0]), abs(b[3])) > 0.16 and not (b[0] < 0 < b[3]): skipped["lateral-arm"] += 1; continue
    if re.search(r"\.(j|el|er|ol|or|o\d+[lr]|e\d+[lr]|i)$", n): skipped["marker"] += 1; continue
    if EXCL.search(n): skipped["excluded-name"] += 1; continue
    s = system_of(o)
    if s is None: skipped["no-system"] += 1; continue
    m = re.search(r"\.(l|r)$", n); side = m.group(1) if m else "m"
    base = re.sub(r"\.(l|r)$", "", n).replace("*", "").strip()
    oid = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-") + ("-" + side if side != "m" else "")
    if oid in seen: skipped["dup-id"] += 1; continue
    seen.add(oid)
    sel.append({"name": n, "id": oid, "label": base, "side": side, "system": s, "tier": tier_of(s, o), "kind": o["kind"], "polys": o.get("polys") or o.get("mesh_polys") or 0})
json.dump(sel, open(f"{S}/selection.json", "w"), indent=0)
print("selected", len(sel), "skipped", dict(skipped))
print("by system:", collections.Counter(x["system"] for x in sel))
print("by tier:", collections.Counter(x["tier"] for x in sel))
print("total polys:", sum(x["polys"] for x in sel), "max", max(sel, key=lambda x: x["polys"])["name"], max(x["polys"] for x in sel))
big = sorted(sel, key=lambda x: -x["polys"])[:15]
print("biggest:", [(x["label"], x["polys"]) for x in big])
