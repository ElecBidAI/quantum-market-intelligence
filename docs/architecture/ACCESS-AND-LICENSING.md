# QMI — Access & Licensing

This is a separate axis of work from the 10-phase quant roadmap
(`QMI-MASTER-ARCHITECTURE.md`): it governs who may call the platform and
what plan they're on, not markets/strategies/risk. It was added after
Phase 9, with zero prior auth code in the repository.

## 1. Principles

- **Licensing is feature-gating by plan, not billing.** There is no
  payment processing anywhere in this repository. A plan (`free` / `pro` /
  `enterprise`) only determines which `Feature`s a user's requests are
  entitled to (`packages/contracts/src/auth.ts`'s `ENTITLEMENTS` map).
  Assigning a plan to an organization today is a direct database write, not
  a checkout flow.
- **Enterprise SSO means OIDC**, not SAML. OIDC covers Okta, Azure
  AD/Entra, Google Workspace, Auth0, and effectively every modern identity
  provider; SAML is a legacy, XML-signature-based protocol with no
  consumer here — deferred (see Section 7).
- **Email + password remains the baseline.** Not every organization
  configures SSO on day one, and it keeps most of the test suite
  infra-free (no live IdP needed).

## 2. Data model (`data/migrations/0008_auth.sql`)

- **`organizations`**: `id`, `name`, `plan` (`free`/`pro`/`enterprise`,
  default `free`).
- **`users`**: `id`, `organization_id` (direct FK — a user belongs to
  exactly one organization; multi-org membership is deferred, see Section
  7), `email` (case-insensitively unique), `password_hash` (nullable —
  SSO-only users never get one), `role` (`member`/`admin`).
- **`sso_connections`**: one row per organization (`UNIQUE(organization_id)`
  — multiple IdPs per org is deferred), `issuer`, `client_id`, and the
  client secret encrypted at rest (Section 5).
- **`sessions`**: opaque-token sessions (Section 3).
- Auth events (`register`/`login`/`login_failed`/`logout`/`sso_login`) are
  written to the existing `audit_events` table from `0001_init.sql`, not a
  new parallel table — its `(event_type, actor, payload, timestamp)` shape
  already fits them.

## 3. Sessions

Sessions are **opaque tokens**, not JWTs. `sessions.token_hash` stores only
a SHA-256 hash of a random 256-bit token (`apps/api/src/session.ts`); the
raw token exists only in the client's cookie. A database leak alone
doesn't yield a usable session, and revocation is a plain row delete — no
JWT-revocation-list problem to solve. Sessions live in Postgres, not Redis:
Redis is optional/absent-tolerant infrastructure elsewhere in this repo
(`services/market-data`'s Redis pub/sub), and auth must work even when
`REDIS_URL` is unset.

### Cookie transport: same-origin via a proxy

`apps/web/next.config.mjs` proxies `/api/:path*` to apps/api. From the
browser's perspective every request — including the SSE market stream —
is same-origin, so the session cookie only needs `SameSite=Lax` (`httpOnly`
always; `Secure` in production only) instead of cross-site
`SameSite=None`, which would otherwise force HTTPS even in local dev. All
of `apps/web`'s calls to apps/api go through `apps/web/lib/api-client.ts`'s
`apiFetch`/`apiStreamUrl`, which target `/api/...` (relative), never
apps/api's own origin directly.

## 4. Entitlements

`packages/contracts/src/auth.ts` defines `Feature` (a string union — today
just `"market-data:read"`) and `ENTITLEMENTS: Record<Plan, ReadonlySet<Feature>>`,
the single source of truth for what each plan grants.
`apps/api/src/entitlements.ts` exports `protect(deps, feature)` —
`authenticate` (validates the session, loads `request.user`) bundled with
`requireEntitlement(feature)` (403s if the plan lacks it). `protect()` is
the **only** exported way to gate a route: a route can use `authenticate`
alone (e.g. `/auth/me`, which only needs identity), but `requireEntitlement`
is never exported in a form that can be wired without `authenticate` first
— the same structural-enforcement pattern used elsewhere in this repo
(e.g. `paper_execution.orders.create_order_from_decision` cannot construct
an order from a `REJECT` decision).

**Adding a new gated feature** is a two-line change: add the string to
`Feature`, add it to whichever plans' sets in `ENTITLEMENTS`, then call
`protect(deps, "the-new-feature")` on the route.

`/market/latest` and `/stream/market` are the first real routes gated this
way (all three plans currently grant `market-data:read`, so this doesn't
change who can reach them today — it proves the mechanism end to end for
the next feature that *will* differentiate by plan).

## 5. Password hashing & SSO secret encryption

- Passwords are hashed with **argon2id** (`apps/api/src/password.ts`),
  the current OWASP-recommended default; unlike bcrypt it has no silent
  72-byte input truncation.
- SSO client secrets are encrypted at rest with **AES-256-GCM**
  (`apps/api/src/sso-crypto.ts`) using a key from `AUTH_ENCRYPTION_KEY`.
  The IV and GCM auth tag are stored separately from the ciphertext, so a
  tampered value fails decryption explicitly instead of silently producing
  garbage. **If `AUTH_ENCRYPTION_KEY` is unset, `apps/api` does not
  register the SSO routes at all** (mirrors the existing
  `if (deps.market)` opt-in pattern for infra-dependent routes) — email/
  password auth still works without it. There is no silent fallback to an
  unencrypted secret.

## 6. OIDC flow

`apps/api/src/routes/sso.ts`:

1. `GET /auth/sso/:organizationId/start` loads the org's `sso_connections`
   row, decrypts the client secret, and calls `openid-client`'s
   `discovery()` against the connection's `issuer` (a live HTTP call in
   production — an admin only has to provide `issuer`/`client_id`/
   `client_secret`, not every individual endpoint URL). It generates
   `state`, `nonce`, and a PKCE `code_verifier`/`code_challenge`, stashes
   them in a short-lived (10 minute) httpOnly `qmi_sso_state` cookie (there
   is no server-side session yet at this point — the cookie is the
   CSRF-protection mechanism), and redirects to the IdP.
2. `GET /auth/sso/:organizationId/callback` reads that cookie, re-runs
   discovery, and calls `authorizationCodeGrant()` with the expected
   state/nonce/PKCE verifier. The ID token's `email` claim (requested via
   `scope=openid email profile`) determines the account: if no user with
   that email exists in the organization yet, one is **just-in-time
   provisioned** (`role: "member"`, `password_hash: NULL`); if a user with
   that email exists in a *different* organization, the callback 403s
   rather than silently reassigning them. Either way, a normal session
   starts exactly as `/auth/login` would.
3. Every discovery/token-endpoint call is injectable
   (`SsoRouteDeps.fetchImpl`), the same dependency-injection idiom
   `services/market-data`'s adapters use for their WebSocket connections —
   `apps/api/test/sso-routes.test.ts` runs the full flow, including real
   RS256 ID-token signature verification, against a fake in-process IdP
   with zero real network calls.

Discovered configuration is **not cached** across requests — every
start/callback pair re-discovers. That's a documented future optimization,
not a correctness requirement.

## 7. Deferred

Explicitly out of scope for this slice, not silently missing:

- **SAML** — see Section 1.
- **Self-serve SSO admin UI** — `sso_connections` rows are inserted
  directly via SQL for now; there is no admin-facing configuration screen.
- **Billing / payments** — plans are assigned directly in the database.
- **Multi-org-per-user membership** — `users.organization_id` is a direct
  FK, not a join table. Cheap to add later; expensive to retrofit around
  live session/entitlement code, but nothing needs it yet.
- **Multiple SSO connections per organization** — `sso_connections.organization_id`
  is `UNIQUE`.
- **Password reset / forgot-password flow** — no `password_reset_tokens`
  table exists.
- **Email verification** — a registered email is trusted as entered.
- **Login-attempt rate limiting.**
- **Roles beyond `member`/`admin`** — no org-scoped custom roles.
- **Session cleanup job** — expired sessions are rejected at lookup time
  (`expires_at` check), not purged from the table. A cleanup job is a
  later addition, not a correctness requirement.
- **Caching discovered OIDC configuration** — see Section 6.
