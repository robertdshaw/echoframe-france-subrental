# Deploy notes — EchoFrame France Subrental

## First-time deploy via Render Blueprint

1. Push the repo to GitHub.
2. Render dashboard → **New → Blueprint** → point at the repo.
3. Render reads `render.yaml` and provisions both services:
   - `echoframe-france-api` (Python web service · Frankfurt)
   - `echoframe-france-web` (static site)
4. Once both build, set secrets in the Render dashboard:
   - `ANTHROPIC_API_KEY` (optional — enables Claude narrative polish)
   - `NEWSDATA_API_KEY` (optional — enables live news feed)
   - `INSEE_API_KEY`, `BDF_API_KEY` (optional — enables live macro)
   - `VITE_API_URL` on the frontend → set to the live API URL
     (e.g. `https://echoframe-france-api.onrender.com`)
5. Trigger a redeploy on the static site so the env var bakes into
   the bundle.

## Locking CORS to the frontend origin

The Blueprint ships `CORS_ORIGINS` with the default
`https://echoframe-france-web.onrender.com` plus localhost ports for
dev. If your static site lands at a different URL (or you bring a
custom domain), update the JSON-array env var in the Render dashboard.

The Argentina build's CORS bug is encoded as a guard in
`backend/config.py:get_cors_settings()` — `allow_credentials` is
derived from whether the origin list contains `"*"`. Wildcard +
credentials together breaks browser preflights silently.

## Database

SQLite at `./echoframe_france.db` for the MVP. Render's free tier
gives ephemeral disk; the seed reloads automatically on each boot.

For production, swap `DATABASE_URL` to a Postgres URL and run alembic
migrations (alembic is in requirements; migrations scaffold not yet
added).

## Known limitations

- The backend prefetches zone forecasts in a fire-and-forget
  background task, so the first request after a cold start may still
  be slow. Subsequent requests are served from the in-memory cache
  (TTL 1 hour).
- The lifespan seeder runs in a thread-safe SQLAlchemy session but
  the SQLite file is single-writer; concurrent writes from multiple
  workers are not supported. Stay on one worker until Postgres.
- React Query default `staleTime` is 60s, so navigating away and back
  doesn't re-hit the API. Tweak in `frontend/src/main.tsx` if needed.
