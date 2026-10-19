# 15-minute demo script

Goal: show a working, secure, observable system end to end, and explain the decisions behind it.
Rehearse once with a timer. If something breaks live, say so calmly and switch to the backup.

## Before you start (do this 30 minutes earlier)

- [ ] `GET /health` on the live URL returns `ok`.
- [ ] Migration `0002` has been applied to the Railway database, and `SECRET_KEY` is 32+ characters.
- [ ] Phone or emulator is charged, the **release** APK is installed, and you are logged **out**.
- [ ] Swagger (`/docs`), the Railway log view, the Sentry project and the GitHub Actions page are
      open in separate browser tabs.
- [ ] A fresh email address ready for registering (for example `demo+1@example.com`).
- [ ] Sentry: `ENABLE_DEBUG_ROUTES` is **off** until you need it (step 8).
- [ ] **Backup:** a screen recording of the full flow, saved locally.
- [ ] Optional, for the token-refresh moment in step 5: temporarily set
      `ACCESS_TOKEN_EXPIRE_MINUTES=1` on Railway, and **set it back to 30 afterwards**.

## Timeline

| Time | Step | What to do and say |
|---|---|---|
| 0:00 | **1. The problem** | One sentence: a task manager where each user only ever sees their own tasks, with a backend I made production-ready this week. |
| 0:45 | **2. Architecture** | Show `docs/architecture.png`. Phone to Railway over HTTPS; FastAPI in four layers; Postgres. Point out that the Flutter domain layer has no framework imports. |
| 2:30 | **3. The app: register and log in** | Register a new account, log in. Mention tokens are stored in the Android Keystore (secure storage), not plain preferences. |
| 4:00 | **4. The app: CRUD** | Create two tasks, edit one (status to *in progress*), mark one done, delete one. Pull to refresh. Show the empty state by deleting the last task. |
| 5:30 | **5. Silent token refresh** | Wait out the 1-minute token (see checklist), pull to refresh. In the Railway logs show `POST /auth/refresh 200` followed by the retried `GET /tasks 200`. Say: the user noticed nothing. |
| 6:30 | **6. Swagger and ownership** | In `/docs`, log in as a *second* user and call `GET /tasks/{id}` with the first user's task ID. Result: `404`, not `403`, so the API never confirms it exists. |
| 7:30 | **7. Security live** | (a) Create a task whose title is `<b>Hi</b><script>alert(1)</script>` and show it stored as `Hi`. (b) Fire 6 bad logins in a row and show the `429` with `Retry-After`. (c) Show the response headers in the browser dev tools (nosniff, CSP, HSTS). |
| 9:30 | **8. Observability** | Take a `request_id` from an error response, search for it in the Railway logs, and show the JSON line. Then set `ENABLE_DEBUG_ROUTES=true`, redeploy, open `/api/v1/debug/sentry-test`, and show the event in Sentry with the same `request_id`. Turn the flag off again. |
| 11:30 | **9. Engineering quality** | GitHub Actions page: lint, tests, audit, build all green. Mention 158 backend tests at 97.6% coverage, plus 36 Flutter tests. Show the audit story: 39 vulnerabilities found, 0 after, and why `python-jose` became `PyJWT`. |
| 13:00 | **10. A decision and a mistake** | Decision: Riverpod over BLoC (the ADR). Mistake: the load test that measured my tool instead of my API, or the auto-fix that deleted an import Alembic needed. Both show verifying instead of assuming. |
| 14:00 | **11. Limitations** | In-memory rate limits, no token revocation, no password reset. Say what you would do next. |
| 14:30 | **12. Questions** | |

## Likely questions, with short answers

- **Why 404 instead of 403 for another user's task?** So the API does not reveal that the task exists.
- **Why a refresh token at all?** Short access tokens limit the damage of a leak, and the refresh
  token keeps users from logging in every 30 minutes.
- **How do you stop SQL injection?** The ORM sends values as bound parameters, and I also escape
  LIKE wildcards in search text. A test stores `'; DROP TABLE tasks; --` and finds it as plain text.
- **What is CSRF and does it apply?** An attack that relies on browsers sending cookies
  automatically. This API uses an `Authorization` header, so it does not apply.
- **What would break first at scale?** The in-memory rate limiter (needs Redis) and title search
  (needs a trigram index).
- **How do you know the index helped?** I measured it: 5.17 ms down to 0.13 ms on 300,000 rows.

## If something goes wrong

| Problem | Do this |
|---|---|
| Live API unreachable | Play the screen recording; say the Railway service is restarting. Show the local Docker version if it is running |
| App shows a network error | Pull to refresh to show the retry, or open `/health` to see whether the server is up |
| Hit `429` by accident | Say "that is the rate limiter working", and wait for `Retry-After` |
| Sentry event is slow to appear | Move on and come back at the end |
