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
