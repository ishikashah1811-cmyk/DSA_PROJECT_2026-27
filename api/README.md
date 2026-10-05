# api/: ContentIQ REST API

FastAPI over the engine. The engine never imports from here; this layer stores posts in SQLite, turns uploaded files into `Post` objects and calls `AnalyticsService`.

## Run locally

```bash
# from the repository root
pip install -e engine -r api/requirements.txt
cp .env.example .env
uvicorn api.main:app --reload --env-file .env
```

Open http://localhost:8000/docs for interactive documentation of every endpoint. On first start, an empty database is filled with the 300 synthetic posts in `data/sample/sample_posts.csv`; set `SEED_SAMPLE=false` to start empty.

## Endpoints (API contract v0.1, plan Section 5.5)

| Method and path | Purpose | Request | Response |
|---|---|---|---|
| `GET /api/health` | Liveness check | | `{status, posts}` |
| `POST /api/posts/import` | Upload posts | multipart: `file` (CSV, or Instagram JSON), optional `account`, `followers` | `{imported, skipped, total_posts}` |
| `GET /api/posts` | List stored posts | `limit` (1–500), `offset` | `[{id, account, caption, timestamp, hashtags, likes, comments, followers}]` |
| `DELETE /api/posts` | Remove all posts (demo reset) | | `{imported, skipped, total_posts}` |
| `POST /api/duplicates/run` | Run Module 1 | JSON, all optional: `shingle_type`, `k`, `num_hashes`, `bands`, `rows`, `threshold`, `min_shingles`, `verify`, `bucket_cap`, `seed` | `{run_id, n_posts, n_flagged, n_exact_groups, n_candidates, n_pairs, n_clusters, runtime_ms}` |
| `GET /api/duplicates/clusters` | Clusters of a run | `run_id` (default: latest) | `[{cluster_id, size, post_ids, representative_id, representative_caption, min_sim, avg_sim}]` |
| `GET /api/hashtags/suggest` | Autocomplete | `prefix`, `k` (1–50) | `[{tag, count}]` |
| `GET /api/hashtags/top` | Top-K ranking | `k`, `min_count`, `m` | `[{tag, count, mean_engagement, score}]` |
| `GET /api/benchmark` | LSH vs brute force | | `[{n, brute_ms, lsh_ms, recall, candidates}]` |

Compared with the v0.1 draft, these responses add a few fields (`n_flagged`, `n_exact_groups`, `representative_*`, `timestamp`, `total_posts`); none of the draft's fields were removed or renamed. Errors use FastAPI's `{"detail": ...}` with status 404 (no such run), 413 (upload too large) or 422 (invalid input, e.g. `bands * rows != num_hashes`).

## Importing data

- **CSV:** a header row with a `caption` column; optional `id`, `account`, `timestamp` (ISO 8601 or Unix seconds), `likes`, `comments`, `followers`. Rows without a caption or with unreadable numbers are skipped and counted.
- **Instagram JSON:** the "Download your information" `posts_1.json` (caption in `title`, time in `creation_timestamp`) or Graph API media (`caption`, `timestamp`, `like_count`, `comments_count`). Instagram's export writes UTF-8 text as escaped Latin-1; the adapter repairs it. Field names are provisional until a team export is checked; only `ingest/instagram.py` should need to change.
- **Privacy:** account names are replaced by a stable anonymous id (`acc_` + hash) before anything is stored. IDs already in `acc_...` form are kept.

## Tests

```bash
pytest api/tests      # contract tests: every endpoint returns the agreed JSON shape
```

## Deploy (Render)

`render.yaml` at the repository root describes the web service. Render's disk is temporary on the free plan, so the SQLite database is rebuilt from the sample CSV on each start; uploads last until the next restart or deploy. Set `CORS_ORIGINS` to the Vercel URL of the dashboard.
