# Mesh pipeline (Z-Anatomy → packs)

1. Download `Z-Anatomy.zip` from https://github.com/Z-Anatomy/Models-of-human-anatomy (CC BY-SA 4.0) and unzip `Z-Anatomy/Startup.blend`.
2. Install Blender (`brew install --cask blender`).
3. Inspect:  `blender -b Startup.blend --python inspect_blend.py -- objects.json` and `... --python inspect_curves.py -- curves.json`
4. Select head & neck objects and assign systems/tiers: `python3 select.py <dir containing zanatomy_objects.json and zanatomy_curves.json>` → `selection.json`
5. Export: `blender -b Startup.blend --python export_meshes.py -- selection.json <mesh_dir> 12000` → `<mesh_dir>/*.bin` + `manifest.json`
6. Build the page: `python3 ../build3d.py` (reads `../meshes` by default) → `lab3d.html`, `packs/`, `packs_b64/`, `docs/` (the hosted site root)

## Branches hidden inside fused curves

Many Z-Anatomy nerves and vessels are one curve object holding several splines (the trunk plus its branches), so a
plain export fuses them under the parent's name. To separate them:

1. `blender -b Startup.blend --python export_splines.py -- selection.json <outdir>` writes every spline of every
   multi-spline curve as its own mesh plus `splines.json` (centrelines). Copy the output into `meshes/splines/`.
2. Name the splines in `data/branches.json` (whole splines, or a stretch of one between two length fractions).
3. `python3 tools/split_branches.py` replaces the fused meshes in `meshes/manifest.json` with the named pieces.
   It is re-runnable; unnamed pieces keep the parent's label.
4. Map new labels to cards in `data/label_map.json` and to their whole structure in `data/label_parents.json`, then
   run `build3d.py`.

## Training content (Surgery and Scope modes)

- `data/procedures/<id>.json`: one surgical walkthrough each. A step has `view` (`from`, `systems`, `peel`), `focus` (highlighted
  blue), `risk` (amber; a model label or `card:<id>` for a structure with no geometry), cumulative `hide`, per-step `ghost`,
  `landmarks`, `pearl` and an optional `check` (click-to-identify). Labels must match the model exactly; `build3d.py` embeds the
  files in `PROC_ORDER`. Each file's `notes` field records what the model lacks and what the author was unsure of; it is not shipped.
- `data/scope.json`: the nasopharyngoscopy route (`path`, 1 mm spacing), region texts and landmark `anchors`. Regenerate the path
  with `tools/scope_path.py` (needs numpy; Blender's bundled Python has it), which centres a hand-set waypoint route between the
  airway walls. `palate_offset` moves the soft palate and uvula in Scope mode only, to open the velopharyngeal port.
