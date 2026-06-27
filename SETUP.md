# SETUP.md — Assumptions & Where to Change Things

This file documents every assumption made during implementation so you know exactly where to pull levers.

---

## Access Control

**Assumption:** One shared site password gates the entire app. No per-user accounts.

- **Change the password:** Set the `SITE_PASSWORD` environment variable. Locally, add it to `.env` and load with `python-dotenv`, or just `export SITE_PASSWORD=yourpass` before `flask run`. On Render, set it in the Environment tab.
- Default fallback (if unset): `minecraft` — change this before sharing the link publicly.

---

## Friends Seed List

**Assumption:** The Friends list is seeded with `["Will", "Alex", "Sam", "Jordan"]` on first startup.

- **Change names:** After the app is running, go to **Settings → Friends List** and rename/remove/add from there. No code change needed.
- **Change the seed:** Edit `FRIEND_SEED` in `app.py` (line ~17). Seed only runs on a fresh database (when the `friends` table is empty), so changing it won't affect an existing deployment.

---

## Idea Seed List

**Assumption:** 30 curated build ideas across 5 categories are seeded on first startup. They are read-only in the UI (no edit/delete for seed ideas).

- **Add or remove ideas from the seed:** Edit `IDEA_SEED` in `app.py` (line ~20). Same caveat: only applies to a fresh database.
- **Add ideas after deployment:** Not currently exposed in the UI — ideas are treated as a curated list. To add one post-deploy, connect to the database directly and insert a row into the `ideas` table.

---

## Base Info Seed

**Assumption:** A single `BaseInfo` row with an empty seed is created on first startup. No locations are pre-seeded.

- **Set the realm seed:** Go to **Base Info** page and type it in.
- **Add named locations:** Use the form on the Base Info page.

---

## Database

**Assumption:** `DATABASE_URL` env var controls the database. Defaults to SQLite (`realm.db`) locally.

- **Local SQLite path:** `realm.db` is created in the project root. Fine for dev; will be wiped on Render free-tier restarts (ephemeral filesystem). Don't use SQLite in production.
- **Production Postgres:** Paste a Neon or Supabase connection string into `DATABASE_URL`. Neon's pooled URL (`postgresql://...@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require`) works well with gunicorn's multiple workers.
- **Schema migrations:** The app calls `db.create_all()` at startup, which creates missing tables but does **not** alter existing ones. If you add a column to a model, either drop and recreate the DB or run a migration manually (e.g. via `psql`). For a future v2, consider adding Flask-Migrate.

---

## Categories

**Assumption:** The 5 categories (`Farms`, `Redstone & Tech`, `Aesthetic & Decoration`, `Infrastructure & Travel`, `Defense & Utility`) are derived from the seeded ideas. They are not a separate table.

- The category dropdowns on proposal/project forms pull from the ideas table plus an "Other" option.
- To add a new category: add at least one idea in that category to `IDEA_SEED`, or after deploy, insert a row directly into the `ideas` table.

---

## Voting

**Assumption:** Voting is friend-name based (not session-user based). Since everyone shares one login, anyone can toggle any friend's vote. This is intentional — it's a trust-based group of friends.

- One vote per friend per proposal, toggle on/off.
- Votes are stored in the `votes` table with a unique constraint on `(project_id, friend_id)`.

---

## Images

**Assumption:** Images are pasted URLs only (no file upload). The `<img>` tag has an `onerror` handler that hides it if the URL is broken or the image fails to load.

- Supported: direct image links from imgur, Discord CDN, any URL ending in an image.
- Not supported: Google Drive links, Dropbox preview links — these don't serve raw images.

---

## Secret Key

**Assumption:** `SECRET_KEY` defaults to a hardcoded dev string if the env var is not set.

- Render's `render.yaml` sets `generateValue: true`, so Render auto-generates a secure key on first deploy.
- **Never use the default dev key in production.** Sessions are signed with this key.

---

## Deployment

**Assumption:** Render free web service + Neon free Postgres tier.

- Render free tier spins down after 15 minutes of inactivity. First request after sleep takes ~30s to wake up. Upgrade to a paid tier to avoid this.
- Neon free tier has a 0.5 GB storage limit and also auto-suspends on inactivity (the DB wakes automatically on connection, adding ~1s to cold starts).
- `gunicorn` is started with `--workers 2`. On Render free (512 MB RAM), 2 workers is safe. Reduce to 1 if you see OOM errors.

---

## What's Not Implemented (Out of Scope for v1)

- Per-user authentication
- Email / push notifications
- Chat / comments on projects
- Map rendering
- File uploads
- Idea CRUD from the UI (ideas are a seeded curated list)
- Automatic vote-threshold promotion (promote is always manual)
