# Mesh pipeline (Z-Anatomy → packs)

1. Download `Z-Anatomy.zip` from https://github.com/Z-Anatomy/Models-of-human-anatomy (CC BY-SA 4.0) and unzip `Z-Anatomy/Startup.blend`.
2. Install Blender (`brew install --cask blender`).
3. Inspect:  `blender -b Startup.blend --python inspect_blend.py -- objects.json` and `... --python inspect_curves.py -- curves.json`
4. Select head & neck objects and assign systems/tiers: `python3 select.py <dir containing zanatomy_objects.json and zanatomy_curves.json>` → `selection.json`
5. Export: `blender -b Startup.blend --python export_meshes.py -- selection.json <mesh_dir> 12000` → `<mesh_dir>/*.bin` + `manifest.json`
6. Build the page: `python3 ../build3d.py` (reads `../meshes` by default) → `lab3d.html`, `packs/`, `packs_b64/`, `docs/` (the hosted site root)
