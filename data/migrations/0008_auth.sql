-- QMI Access & Licensing schema: user accounts, sessions, and per-org SSO
-- configuration (docs/architecture/ACCESS-AND-LICENSING.md).
--
-- Mirrors packages/contracts/src/auth.ts. This is a separate axis of work
-- from the 10-phase quant roadmap (see that doc) — it governs who may call
-- the platform and what plan they're on, not markets/strategies/risk.
--
-- Auth events (register/login/login_failed/logout/sso_login) are written to
-- the existing `audit_events` table from 0001_init.sql rather than a new
-- parallel table — its (event_type, actor, payload, timestamp) shape
-- already fits them.
--
-- Deliberately NOT created here (see ACCESS-AND-LICENSING.md "Deferred"):
--   - password_reset_tokens: no forgot-password flow this slice.
--   - an organization-membership join table: users.organization_id is a
--     direct FK, i.e. one organization per user by design; multi-org
--     membership is deferred until something actually needs it.
--   - a normalized roles table: role is an inline enum column on users, not
--     org-scoped custom roles.
--   - any session-cleanup job/table: expired sessions are simply rejected
--     at lookup time (expires_at check), not purged. A cleanup job is a
--     later addition, not a correctness requirement.

CREATE TABLE IF NOT EXISTS organizations (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    plan        TEXT NOT NULL CHECK (plan IN ('free', 'pro', 'enterprise')) DEFAULT 'free',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- password_hash is nullable: an SSO-only (JIT-provisioned) user never has one.
CREATE TABLE IF NOT EXISTS users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  UUID NOT NULL REFERENCES organizations(id),
    email            TEXT NOT NULL,
    password_hash    TEXT,
    role             TEXT NOT NULL CHECK (role IN ('member', 'admin')) DEFAULT 'member',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Case-insensitive email uniqueness: plain UNIQUE is case-sensitive in
-- Postgres, which would let "a@x.com" and "A@x.com" collide as different
-- accounts.
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users (lower(email));
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users (organization_id);

-- One OIDC connection per organization this slice (UNIQUE on organization_id
-- enforces it) — multiple IdPs per org is deferred. The client secret is
-- encrypted at rest with AES-256-GCM (apps/api/src/sso-crypto.ts); iv and
-- tag are stored separately from the ciphertext so a tampered value fails
-- decryption explicitly instead of silently producing garbage.
CREATE TABLE IF NOT EXISTS sso_connections (
    id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id           UUID NOT NULL UNIQUE REFERENCES organizations(id),
    issuer                    TEXT NOT NULL,
    client_id                 TEXT NOT NULL,
    client_secret_ciphertext  BYTEA NOT NULL,
    client_secret_iv          BYTEA NOT NULL,
    client_secret_tag         BYTEA NOT NULL,
    created_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Opaque-token sessions: token_hash is a SHA-256 hex digest of the token the
-- client holds in its cookie. The raw token is never stored, so a database
-- leak alone doesn't yield a usable session; revocation is a row delete.
CREATE TABLE IF NOT EXISTS sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id),
    token_hash  TEXT NOT NULL UNIQUE,
    expires_at  TIMESTAMPTZ NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at);
