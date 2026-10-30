# Head and Neck Anatomy Lab 3D

A rotatable 3D head and neck atlas with a skin-to-brain peel, click-to-identify cards and a quiz, written for USMLE Step 2 CK study.

- `docs/` is the deployed site: GitHub Pages publishes it from the `main` branch on every push.
- `template3d.html` + `data/*.json` + `build3d.py` build it: `python3 build3d.py` (reads the mesh export in `meshes/`, not in git; see `tools/README.md` to re-export it).
- `DEPLOY.md` covers hosting and custom domains.

Model data: [Z-Anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy) (CC BY-SA 4.0), derived from BodyParts3D (CC BY-SA 2.1 JP) with cranial nerves from the University of Dundee CAHID (CC BY 4.0). The model data in this repository is shared under CC BY-SA 4.0.
