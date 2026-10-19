# ADR 0001: Use PyJWT instead of python-jose

- **Status:** Accepted
- **Date:** 2026-10-11

## Context

The API signs and verifies JWTs. It started with `python-jose`, as many older FastAPI tutorials
use. The Week 6 dependency audit (`pip-audit`) reported vulnerabilities in `python-jose` 3.3.0:
two fixed in 3.4.0, and a third in its `ecdsa` dependency that has **no fixed version at all**.

## Options considered

1. **Upgrade `python-jose` to the latest release.** Fixes the two direct issues, but the `ecdsa`
   dependency (and its unfixed finding) stays. The project is also barely maintained.
2. **Switch to `PyJWT`.** Actively maintained, small, no `ecdsa` dependency. FastAPI's own
   documentation moved to it for the same reasons.
3. **Use `Authlib` / `joserfc`.** More features than needed (OAuth server, JWE).

## Decision

Use **PyJWT** (option 2).

## Consequences

- Positive: the audit goes from 39 findings to zero; one fewer unmaintained dependency.
- Positive: the change was small. Only `app/core/security.py` and one import in the auth service
  changed, because both libraries expose `encode()` / `decode()`.
- Positive: PyJWT requires explicit `algorithms=[...]` when decoding, which closes the
  algorithm-confusion class of bug. A test checks that an unsigned (`alg: none`) token is rejected.
- Negative: tokens issued before the switch remain valid (same HS256 format and secret), so no
  one is logged out, but there was also no chance to rotate the secret as part of the change.
  Rotating `SECRET_KEY` is a separate, deliberate step.
- Negative: PyJWT raises different exception classes; `app/core/security.py` re-exports them as
  `TokenError` so the rest of the code does not depend on the library.
