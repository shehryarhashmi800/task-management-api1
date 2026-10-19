# Authentication flow

How the Flutter app and the API handle register, login, normal requests and an expired token.
(The diagram is Mermaid, which GitHub draws automatically.)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant App as Flutter app<br/>(Riverpod + use cases)
    participant Int as AuthInterceptor<br/>(Dio)
    participant Store as Secure storage
    participant API as FastAPI
    participant DB as PostgreSQL

    rect rgb(238, 242, 255)
    Note over User,DB: A. Register, then log in
    User->>App: email, username, password
    App->>API: POST /auth/register
    API->>DB: INSERT user (bcrypt hash)
    API-->>App: 201 user (no tokens yet)
    User->>App: email, password
    App->>API: POST /auth/login (rate limited per IP)
    API->>DB: SELECT user by email
    API->>API: verify bcrypt hash
    API-->>App: 200 access_token (30 min) + refresh_token (7 days)
    App->>Store: save both tokens
    end

    rect rgb(236, 253, 245)
    Note over User,DB: B. Normal request
    User->>App: open task list
    App->>Int: GET /tasks
    Int->>Store: read access token
    Int->>API: GET /tasks + Authorization: Bearer access
    API->>API: verify signature, expiry, type = access
    API->>DB: SELECT tasks WHERE owner_id = me
    API-->>App: 200 page of tasks
    end

    rect rgb(255, 251, 235)
    Note over User,DB: C. Access token has expired (silent refresh)
    App->>Int: GET /tasks
    Int->>API: GET /tasks + expired access token
    API-->>Int: 401 invalid_token
    Int->>Store: read refresh token
    Int->>API: POST /auth/refresh {refresh_token}
    API->>API: verify signature, expiry, type = refresh
    API-->>Int: 200 new access_token
    Int->>Store: save new access token
    Int->>API: retry GET /tasks (once, new token)
    API-->>App: 200 page of tasks
    Note over User,App: The user notices nothing
    end

    rect rgb(254, 242, 242)
    Note over User,DB: D. Refresh token also rejected
    Int->>API: POST /auth/refresh
    API-->>Int: 401
    Int->>Store: clear tokens
    Int-->>App: session expired event
    App-->>User: back to the login screen
    end
```

## Details worth knowing

- **One refresh at a time.** If several requests get a 401 together, the interceptor performs a
  single refresh and the others wait for its result instead of each calling `/auth/refresh`.
- **Retried once.** A request that fails again after refreshing is not retried a second time, which
  prevents an endless loop.
- **Rate limits.** `login`, `register` and `refresh` are limited per IP address. If the app is
  rate limited it gets `429` with a `Retry-After` header and shows the server's message.
- **Why 404 and not 403 for someone else's task.** The API answers `404` so it never confirms that
  another user's task exists.
