# Performance notes

Everything here was measured on 11 October 2026 in a **1-CPU sandbox** where the load tool,
the API and PostgreSQL all shared one core. Treat the numbers as *relative* evidence (before vs.
after, endpoint vs. endpoint), not as a capacity promise for Railway.

## 1. The task-list index (measured before and after)

The list endpoint runs: `WHERE owner_id = ? ORDER BY created_at DESC LIMIT 20`.

Test data: 300,000 tasks across 100 users (3,000 tasks per user), `ANALYZE` run before measuring,
best of 5 runs of `EXPLAIN ANALYZE`.

| | Indexes used | Plan | Time |
|---|---|---|---|
| Before (migration 0001) | `ix_tasks_owner_id` | Bitmap scan of the user's 3,000 rows, **then sort them** | **5.17 ms** |
| After (migration 0002) | `ix_tasks_owner_created (owner_id, created_at)` | Index scan **backwards**, stop after 20 rows, no sort | **0.13 ms** |

About **40x faster**, and the gap grows with the number of tasks per user (the "before" plan sorts
every one of them).

Migration `0002` also drops two indexes that could never help:

- `ix_tasks_owner_id` is redundant, because the new composite index starts with `owner_id`;
- `ix_tasks_title` cannot serve `ILIKE '%text%'` (a plain B-tree index only helps prefix matches),
  so it only slowed down writes.

`ix_tasks_status` and `ix_tasks_priority` were kept; they are small (about 2 MB each at 300k rows).

**Known limit:** title search is still a sequential scan over the user's own tasks. That is fast
for personal task lists. For very large lists, the next step would be a `pg_trgm` GIN index.

## 2. Load test (stretch goal)

Tool: ApacheBench (`ab -n 1000 -c 10`), 300,000 rows in the database, one uvicorn process, JSON
logs at WARNING level, production settings, authenticated as one user with 3,000 tasks.

| Endpoint | Requests/s | p50 | p95 | p99 | Failed |
|---|---|---|---|---|---|
| `GET /health` | 352 | 22 ms | 66 ms | 93 ms | 0 |
| `GET /api/v1/tasks?page_size=20` | 207 | 44 ms | 66 ms | 138 ms | 0 |
| `GET /api/v1/tasks?page_size=100` | 155 | 59 ms | 101 ms | 128 ms | 0 |

Reading it: the cost of a list request is mostly JSON serialisation and authentication, not the
database query (0.13 ms). Larger pages cost more because more rows are validated and serialised.
That is why the API caps `page_size` at 100 and the Flutter app asks for 20.

### A measurement mistake worth remembering

My first load test used a Python script with threads and showed `/health` at only 31 requests per
second, almost the same as the list endpoint. A trivial endpoint being as slow as a heavy one
meant the **tool** was the bottleneck, not the API. Re-measuring with `ab` gave 352 req/s. Always
check that a benchmark can distinguish a fast thing from a slow thing before trusting it.

## 3. Not done

- Caching headers (`ETag` / `Cache-Control`) on the list endpoint (optional stretch goal). Task
  lists are per-user and change often, so the benefit is small compared with the added complexity.
- Load testing on the real Railway deployment.
