# Publish the Frío dashboard on Netlify (you already have Netlify + GitHub linked)

**Important:** Netlify hosts *static* sites, not the Python server. So we publish a
**static snapshot** of the dashboard — a single `index.html` the agent generates from
your data. Netlify (already linked to GitHub) publishes it automatically on every push.

```
  agent  ──exports──►  frio-agent/public/index.html  ──git push──►  GitHub  ──auto──►  Netlify (live URL)
```

**How "you connect me to Netlify" actually works:** I don't log into your Netlify. The
bridge is GitHub — I generate the snapshot and push it; your Netlify↔GitHub link does
the publishing. Nothing else to connect.

## One-time setup in Netlify (≈3 minutes)
1. Netlify ▸ **Add new site** ▸ **Import an existing project** ▸ pick your GitHub repo
   `sebasvelasquez1/Auto-GPT`, branch `claude/frio-shopping-agent-oxyduf`.
2. Build settings:
   - **Base directory:** `frio-agent`
   - **Build command:** *(leave empty)*
   - **Publish directory:** `public`
3. **Deploy.** Netlify gives you a URL like `https://your-site.netlify.app`.

(There's a `frio-agent/netlify.toml` with these settings already; just confirm them.)

## Update the numbers later
Re-generate the snapshot and push — Netlify re-publishes automatically:
```bash
cd frio-agent
frio export-site --out public
git add public/index.html && git commit -m "update dashboard" && git push
```

## Privacy / password — read this (honest)
- A Netlify URL is **public by default**. While the dashboard shows **example/offline**
  data, that's fine.
- **Before it shows real financials**, lock it down — options:
  - **Netlify password protection** (site-wide single password) — a **Pro** feature.
  - **Netlify Identity** (free tier) — a login gate, a little setup.
  - Or keep the truly private version **local** (`frio dashboard` on your computer).
- The snapshot is **read-only** — even public, it can't spend money or launch/publish.

## Note
It's a **snapshot** (updates when you re-export + push), not a live real-time feed.
For a panel you check periodically, that's exactly what you want.
