# Deploy the Frío dashboard online (with login)

The dashboard is **read-only** and **password-protected**. Hosting it online lets you
open it from your phone. Two things are true and important:

1. **You** create the (free) hosting account and set the password — I don't publish
   your business data on your behalf.
2. **Shared database:** for the online dashboard to show real data, the agent and the
   dashboard must use the **same** cloud database (Postgres). The local SQLite file on
   your computer is not reachable from the internet. Our code already supports Postgres
   — you just point `FRIO_DATABASE_URL` at it.

```
   your computer: agent  ──writes──►  ☁ Postgres (cloud)  ◄──reads──  ☁ dashboard (online, login)
   FRIO_DATABASE_URL = the SAME postgres URL on both sides
```

## Easiest path — Render.com (free tier, automatic HTTPS)

1. Create a free account at https://render.com and connect your GitHub
   (`sebasvelasquez1/Auto-GPT`, branch `claude/frio-shopping-agent-oxyduf`).
2. **Database:** New ▸ PostgreSQL ▸ Free ▸ Create. Copy its **Internal** and
   **External** connection URLs.
3. **Web service:** New ▸ Web Service ▸ pick the repo ▸ set:
   - Root Directory: `frio-agent`
   - Runtime: **Docker** (it finds `frio-agent/Dockerfile`)
   - Health check path: `/healthz`
4. **Environment variables** on the web service:
   - `FRIO_DATABASE_URL` = the Postgres **Internal** URL from step 2
   - `FRIO_DASHBOARD_USER` = `frio`
   - `FRIO_DASHBOARD_PASSWORD` = a **strong** password you choose
5. Create ▸ wait for the build ▸ open the `https://…onrender.com` URL ▸ log in.

> One-click alternative: copy `render.yaml` to the repo root and use Render ▸
> New ▸ Blueprint. It provisions the DB + service together; you only set the password.

## Put REAL data in it
Run the agent against the SAME database (use the Postgres **External** URL locally):
```bash
export FRIO_DATABASE_URL='postgresql://…the external url…'
frio research run --seed "Spiritual Gangster"
frio product discover --niche spirituality
# …whatever you run writes to the cloud DB; the online dashboard shows it.
```

## Security checklist (read before going live)
- ✅ Use a **strong, unique** password (the login is sent over HTTPS, which Render provides).
- ✅ Keep the URL private; don't post it anywhere.
- ✅ The dashboard is **read-only** — it cannot spend money, launch ads, or publish.
  Those stay in the CLI behind their caps + your approval.
- ⚠️ It shows business financials. If you'd rather not expose them at all, keep it
  **local** (`frio dashboard` on your computer) — that's the safest option.
- ⚠️ Render's free tier sleeps when idle and the free Postgres expires after ~30 days;
  for ongoing use, upgrade the DB to a paid plan (small monthly cost).

## Other hosts
Railway and Fly.io work the same way (Docker + a Postgres add-on + the same two env
vars). The Dockerfile is host-agnostic.
