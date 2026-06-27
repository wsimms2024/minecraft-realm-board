# Minecraft Realm Board

A shared project board for a Minecraft realm. Browse build ideas, propose projects, vote, and track them through to completion.

## Local Setup

```bash
pip install -r requirements.txt
flask run
```

Open http://localhost:5000. Default password: `minecraft` (change via `SITE_PASSWORD` env var).

SQLite database is created automatically at `realm.db` on first run. Seed data (ideas, friends) is inserted once.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SITE_PASSWORD` | `minecraft` | Shared password for the whole site |
| `SECRET_KEY` | dev key | Flask session secret — **always set in prod** |
| `DATABASE_URL` | `sqlite:///realm.db` | SQLAlchemy DB URL; use Postgres in prod |

## Deploying to Render

1. Push this repo to GitHub.
2. Create a free Postgres database on [Neon](https://neon.tech) or [Supabase](https://supabase.com). Copy the connection string.
3. In [Render](https://render.com), create a new **Web Service** → connect your repo.
4. Render will detect `render.yaml` automatically. Set these environment variables in the dashboard:
   - `SITE_PASSWORD` → your chosen password
   - `DATABASE_URL` → your Neon/Supabase connection string (use the **pooled** URL from Neon)
5. Deploy. The app initialises the DB schema and seed data on first startup.

To redeploy after code changes: push to GitHub → Render auto-deploys.

## Stack

- Backend: Python / Flask / Flask-SQLAlchemy
- Frontend: Jinja2 + HTMX + Tailwind CSS (CDN, no build step)
- DB: SQLite locally, Postgres in production
