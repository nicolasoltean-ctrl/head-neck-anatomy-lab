# Putting the Head and Neck Anatomy Lab on your own domain

The 3D lab is a static site: the `site/` folder (`index.html`, `404.html`, `robots.txt`, and `packs/*.pack`, about 21 MB of mesh data).
The earlier flat 2D plate is retired; `build.py` still writes it to `site2d/` if you ever want it, but it is not part of the hosted site.
No server, database, or build step is needed on the host. Any static host works; the steps below use
Cloudflare because it can hold both the domain and the hosting, so DNS is one click.

Everything here takes about 20 minutes the first time. Future updates are a single re-upload.

---

## 1. Register the domain

1. Go to <https://domains.cloudflare.com> (or Porkbun / Namecheap if you prefer) and search for `headandneck.io`.
   A registry lookup on 2026-10-29 showed no record for it, but the registrar's search is the final word.
2. Buy it. A `.io` domain is typically $35–60 per year. Turn on auto-renew so the site never lapses.
3. Keep WHOIS privacy on (Cloudflare does this by default).

If `headandneck.io` is taken after all, `headneck.io` also showed no registration.

## 2. Create the site on Cloudflare Pages

1. In the Cloudflare dashboard, open **Workers & Pages → Create → Pages → Upload assets**.
2. Name the project (for example `headandneck`).
3. Drag the **contents** of the `site/` folder (`index.html`, `404.html`, `robots.txt` and the `packs/` folder) into the upload box,
   not the folder's parent. Click **Deploy site**. The 3D lab is the home page.
4. You get a temporary URL like `https://headandneck.pages.dev`. Open it on your phone and laptop to confirm
   the model loads, peels and the quiz works.

Alternatives that work the same way with a drag-and-drop upload: Netlify (<https://app.netlify.com/drop>)
and Vercel. GitHub Pages works too if you want version history: commit `site/` to a repo, enable Pages on it,
and add a file named `CNAME` containing `headandneck.io`.

## 3. Attach the domain

1. In the Pages project, open **Custom domains → Set up a custom domain** and enter `headandneck.io`.
2. Because the domain is on Cloudflare, it adds the DNS record for you. Accept it.
3. Add `www.headandneck.io` the same way so both forms work (Cloudflare redirects `www` to the apex).
4. HTTPS is issued automatically. It is usually live within minutes; allow up to an hour.

If the domain is registered elsewhere, add a **CNAME** record at your registrar pointing `headandneck.io`
(or `@`) to `headandneck.pages.dev`, and the same for `www`. Registrars that do not allow a CNAME on the
apex offer an ALIAS/ANAME record, which does the same job.

## 4. Updating the site later

1. Edit the card data in `data/*.json` or the viewer in `template3d.html`.
2. Rebuild:

   ```bash
   python3 build3d.py <mesh_dir>
   ```

   `<mesh_dir>` is the folder of exported `.bin` meshes produced from the Z-Anatomy Blender file
   (see `tools/README.md`; the meshes only need re-exporting if you change which structures are included).
   This refreshes `lab3d.html` (the claude.ai artifact version) and `site/` (the standalone version).
3. In Cloudflare Pages, open the project → **Create new deployment** → upload the `site/` folder contents again.
   The previous version stays available under Deployments if you need to roll back.

## What to expect once it is public

- Anyone with the URL can open it. There is no login and nothing is tracked or stored on a server; quiz scores
  live only in the visitor's own browser.
- A full visit downloads about 22 MB of meshes once (the browser caches them); free tiers cover this comfortably.
- The page loads two Google Fonts (Spectral and IBM Plex), three.js from cdnjs, and its mesh packs from `packs/`.
- The 3D model is derived from Z-Anatomy (CC BY-SA 4.0) and BodyParts3D; keep the attribution line in the page footer when you publish.
- The claude.ai artifact link keeps working independently; both copies are updated by the same build command.
