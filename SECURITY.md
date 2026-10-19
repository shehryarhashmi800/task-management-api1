# Security Policy

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Email the maintainer (Muhammad Shehryar Hashmi) with:

- what you found and where,
- steps to reproduce it,
- the `request_id` from the error response, if there is one.

You will get a reply within 3 working days. This is a student capstone project, so there is
no bounty, but reports are taken seriously and credited if you wish.

## What is protected, and how

| Area | Control | Where |
|---|---|---|
| Passwords | bcrypt hashes, never stored or logged in plain text; 8-128 characters with a letter and a digit | `app/core/security.py`, `app/schemas/user.py` |
| Login timing | A dummy hash is checked when the email is unknown, so response time does not reveal which emails exist | `app/services/auth_service.py` |
| Tokens | JWT (HS256) via PyJWT; short-lived access token, long-lived refresh token; `exp` and `sub` required, token type checked, `alg: none` rejected | `app/core/security.py` |
| Brute force | Rate limits per client IP on login, register and refresh (default 5 / 5 / 30 per minute), `429` with `Retry-After` | `app/core/rate_limit.py` |
| Authorization | Every task query is filtered by owner. Another user's task returns `404`, never `403`, so its existence is not revealed | `app/repositories/task_repository.py` |
| SQL injection | SQLAlchemy sends all values as bound parameters. LIKE wildcards (`%`, `_`) in search text are escaped | `app/repositories/task_repository.py` |
| Stored XSS | HTML tags, script/style contents, control characters and invisible text-direction characters are stripped from titles and descriptions | `app/core/sanitize.py` |
| Input validation | Pydantic validates every body, query and path parameter; length limits on every text field; request bodies over 1 MB get `413` | `app/schemas/`, `app/middleware.py` |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`, `Cross-Origin-Resource-Policy`; `Strict-Transport-Security` in production; `Cache-Control: no-store` on auth routes | `app/middleware.py` |
| CORS | Only origins listed in `CORS_ORIGINS`; only the methods and headers the API uses | `app/main.py` |
| Secrets | Read from environment variables only. In production the app **refuses to start** if `SECRET_KEY` is a known placeholder or shorter than 32 characters | `app/config.py` |
| Error handling | Unexpected errors return a generic message plus a `request_id`; details go to the server log and Sentry only | `app/exceptions.py` |
| Logging | Structured JSON; newlines in URLs are escaped so logs cannot be forged; Sentry is configured not to send request bodies or personal data | `app/core/logging_config.py`, `app/core/observability.py` |
| Dependencies | Audited with `pip-audit` in CI (weekly and on every push); test tools are not installed in the production image | `.github/workflows/ci.yml`, `Dockerfile` |
| CSRF | Not applicable: authentication uses an `Authorization` header, not cookies, so browsers never attach credentials automatically | n/a |
| Transport | HTTPS is terminated by Railway; HSTS tells browsers to insist on it | deployment |

## Dependency audit history

Run on 11 October 2026 with `pip-audit`:

- **Before:** 39 known vulnerabilities in 6 packages (`python-jose`, `ecdsa`, `python-multipart`,
  `starlette`, `python-dotenv`, `pytest`).
- **Actions:**
  - replaced `python-jose` with `PyJWT` (its `ecdsa` dependency has no fix available; see
    [ADR 0001](docs/adr/0001-pyjwt-instead-of-python-jose.md));
  - removed `python-multipart` (the API only accepts JSON, so it was unused);
  - upgraded FastAPI/Starlette, `python-dotenv` and `pytest`;
  - moved `pytest` and other dev tools to `requirements-dev.txt`.
- **After:** `No known vulnerabilities found`.

Re-run it yourself: `make audit`.

## Known limitations (honest list)

- **Rate-limit counters live in memory.** With more than one server process or instance, each
  has its own counters. Fine for one Railway instance; use Redis (`limits` supports it) to scale.
- **The client IP comes from `X-Forwarded-For`** when `TRUST_PROXY_HEADERS` is on (the default in
  production). This relies on Railway's edge replacing client-supplied values. If you move behind a
  different proxy, check how it sets that header first.
- **Login limits are per IP, not per account.** An attacker who rotates IP addresses can still
  guess one account's password slowly. A per-account lockout would close this.
- **Refresh tokens cannot be revoked.** They are stateless; logging out only deletes them on the
  device. Revocation needs a token table (or a `jti` deny-list).
- **No email verification or password reset.**
- **`passlib` is unmaintained.** It works with the pinned `bcrypt==4.0.1`, and no vulnerabilities
  are reported, but a future migration to the `bcrypt` library directly is advisable.
- **Request body size** is checked from the `Content-Length` header only; chunked uploads are not
  limited by the app (Railway's proxy applies its own limits).
