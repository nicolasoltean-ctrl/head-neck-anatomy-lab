# Hosting the Head and Neck Anatomy Lab 3D

The lab is a static site. The `docs/` folder (`index.html`, `404.html`, `robots.txt` and `packs/*.pack`,
about 22 MB of mesh data) is everything a host needs; there is no server, database or build step on the host.

It is published with **GitHub Pages** from the public repository
<https://github.com/nicolasoltean-ctrl/head-neck-anatomy-lab> and lives at

**<https://nicolasoltean-ctrl.github.io/head-neck-anatomy-lab/>**

GitHub Pages serves the `main` branch's `docs/` folder (Settings → Pages → Build and deployment →
Deploy from a branch → `main` / `/docs`). Every push to `main` republishes it within a minute or two.

## Updating the site

1. Edit the card data in `data/*.json` or the viewer in `template3d.html`.
2. Rebuild:

   ```bash
   python3 build3d.py <mesh_dir>
   ```

   `<mesh_dir>` is the folder of exported `.bin` meshes produced from the Z-Anatomy Blender file
   (see `tools/README.md`; the meshes only need re-exporting if you change which structures are included).
   This refreshes `lab3d.html` (the claude.ai artifact version) and `docs/` (the published site).
3. Commit and push:

   ```bash
   git add -A && git commit -m "Describe the change" && git push
   ```

   Every earlier version stays in the git history, so any change can be reverted with `git revert`.

The claude.ai artifact (<https://claude.ai/artifact/PLzhX51wTpv5VSqc7FnQQ1>) is separate: republish
`lab3d.html` to it from a Claude session when you want it to match.

## Attaching your own domain (optional)

1. Buy the domain at a registrar (Cloudflare Registrar, Porkbun or Namecheap; a `.io` is typically $35–60 a year,
   a `.com` $10–15). Keep auto-renew on. A registry lookup on 2026-10-29 showed no record for `headandneck.io`.
2. In the repository, open **Settings → Pages → Custom domain**, enter the domain (for example `headandneck.io`)
   and save. GitHub writes a `CNAME` file into `docs/`; commit it so rebuilds keep it (`build3d.py` never deletes it).
3. At the registrar's DNS page add:
   - four **A** records for the apex (`@`) pointing to `185.199.108.153`, `185.199.109.153`,
     `185.199.110.153` and `185.199.111.153`;
   - one **CNAME** record for `www` pointing to `nicolasoltean-ctrl.github.io`.
4. Back in Settings → Pages, wait for the DNS check to pass, then tick **Enforce HTTPS**. Allow up to an hour.

After that the site answers at the domain and at the github.io address alike.

## What to expect once it is public

- Anyone with the URL can open it. There is no login and nothing is tracked or stored on a server; quiz scores
  and preferences live only in the visitor's own browser.
- A first visit downloads about 22 MB of meshes (cached afterwards). GitHub Pages' soft limit is 100 GB of
  bandwidth a month, far above what a study tool uses.
- The page loads two Google Fonts (Spectral and IBM Plex) and three.js from cdnjs.
- The model is derived from Z-Anatomy (CC BY-SA 4.0) and BodyParts3D; keep the attribution line in the page footer.
- The repository is public, so the card data, viewer code and build scripts are visible to anyone.
