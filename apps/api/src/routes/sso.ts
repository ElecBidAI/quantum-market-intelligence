import type { FastifyInstance } from "fastify";
import * as oidc from "openid-client";
import type { QueryablePool } from "../db.js";
import { createSession, sessionCookieOptions } from "../session.js";
import { decryptSecret } from "../sso-crypto.js";

export interface SsoRouteDeps {
  pool: QueryablePool;
  cookieName: string;
  cookieOptions: ReturnType<typeof sessionCookieOptions>;
  ttlSeconds: number;
  encryptionKey: string;
  /** Externally-reachable base URL of this API (API_PUBLIC_URL), used to build the OIDC redirect_uri. */
  apiBaseUrl: string;
  /**
   * Injectable for tests; defaults to the global fetch. openid-client
   * propagates this into every HTTP call it makes (discovery, token
   * exchange), so tests never hit a real network — same idiom as
   * `createSocket` in services/market-data's Binance adapters.
   */
  fetchImpl?: typeof fetch;
}

interface SsoConnectionRow {
  id: string;
  issuer: string;
  client_id: string;
  client_secret_ciphertext: Buffer;
  client_secret_iv: Buffer;
  client_secret_tag: Buffer;
}

const STATE_COOKIE_NAME = "qmi_sso_state";
const STATE_TTL_SECONDS = 600;

interface StatePayload {
  state: string;
  nonce: string;
  codeVerifier: string;
}

function encodeStateCookie(payload: StatePayload): string {
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");
}

function decodeStateCookie(raw: string): StatePayload | null {
  try {
    return JSON.parse(Buffer.from(raw, "base64url").toString("utf8")) as StatePayload;
  } catch {
    return null;
  }
}

function redirectUri(deps: SsoRouteDeps, organizationId: string): string {
  return `${deps.apiBaseUrl}/auth/sso/${organizationId}/callback`;
}

async function loadConnection(pool: QueryablePool, organizationId: string): Promise<SsoConnectionRow | null> {
  const result = await pool.query<SsoConnectionRow>(
    `SELECT id, issuer, client_id, client_secret_ciphertext, client_secret_iv, client_secret_tag
     FROM sso_connections WHERE organization_id = $1`,
    [organizationId],
  );
  return result.rows[0] ?? null;
}

/**
 * Builds an openid-client Configuration via live discovery
 * (`${issuer}/.well-known/openid-configuration`) — deliberately not
 * hand-configured static endpoints, so an admin only ever has to provide
 * `issuer`/`client_id`/`client_secret`, not every individual endpoint URL.
 * Caching the discovered configuration across requests is a future
 * optimization, not implemented this slice — every start/callback pair
 * re-discovers.
 */
async function buildConfig(deps: SsoRouteDeps, connection: SsoConnectionRow): Promise<oidc.Configuration> {
  const clientSecret = decryptSecret(
    {
      ciphertext: connection.client_secret_ciphertext,
      iv: connection.client_secret_iv,
      tag: connection.client_secret_tag,
    },
    deps.encryptionKey,
  );
  const options = deps.fetchImpl ? { [oidc.customFetch]: deps.fetchImpl } : undefined;
  return oidc.discovery(new URL(connection.issuer), connection.client_id, clientSecret, undefined, options);
}

/**
 * Registers:
 *   GET /auth/sso/:organizationId/start — redirects to the org's configured
 *     IdP with PKCE + state + nonce, stashed in a short-lived httpOnly
 *     cookie (there is no server-side session yet at this point in the
 *     flow, so the cookie is the CSRF-protection mechanism).
 *   GET /auth/sso/:organizationId/callback — completes the Authorization
 *     Code Grant, just-in-time provisions a user if the IdP's email isn't
 *     already registered for this organization, and starts a normal
 *     session exactly like /auth/login would.
 *
 * Only registered by app.ts when AUTH_ENCRYPTION_KEY is configured — see
 * that file and docs/architecture/ACCESS-AND-LICENSING.md.
 */
export function registerSsoRoutes(app: FastifyInstance, deps: SsoRouteDeps): void {
  app.get<{ Params: { organizationId: string } }>(
    "/auth/sso/:organizationId/start",
    async (request, reply) => {
      const { organizationId } = request.params;
      const connection = await loadConnection(deps.pool, organizationId);
      if (!connection) {
        return reply.code(404).send({ error: "sso_not_configured" });
      }

      const config = await buildConfig(deps, connection);
      const state = oidc.randomState();
      const nonce = oidc.randomNonce();
      const codeVerifier = oidc.randomPKCECodeVerifier();
      const codeChallenge = await oidc.calculatePKCECodeChallenge(codeVerifier);

      const authorizationUrl = oidc.buildAuthorizationUrl(config, {
        redirect_uri: redirectUri(deps, organizationId),
        scope: "openid email profile",
        state,
        nonce,
        code_challenge: codeChallenge,
        code_challenge_method: "S256",
      });

      reply.setCookie(STATE_COOKIE_NAME, encodeStateCookie({ state, nonce, codeVerifier }), {
        httpOnly: true,
        secure: deps.cookieOptions.secure,
        sameSite: "lax",
        path: "/",
        maxAge: STATE_TTL_SECONDS,
      });
      return reply.redirect(authorizationUrl.toString());
    },
  );

  app.get<{ Params: { organizationId: string } }>(
    "/auth/sso/:organizationId/callback",
    async (request, reply) => {
      const { organizationId } = request.params;

      const rawState = request.cookies[STATE_COOKIE_NAME];
      reply.clearCookie(STATE_COOKIE_NAME, { path: "/" });
      const statePayload = rawState ? decodeStateCookie(rawState) : null;
      if (!statePayload) {
        return reply.code(400).send({ error: "sso_state_missing_or_expired" });
      }

      const connection = await loadConnection(deps.pool, organizationId);
      if (!connection) {
        return reply.code(404).send({ error: "sso_not_configured" });
      }

      const config = await buildConfig(deps, connection);
      const currentUrl = new URL(request.url, deps.apiBaseUrl);

      const tokens = await oidc.authorizationCodeGrant(config, currentUrl, {
        expectedState: statePayload.state,
        expectedNonce: statePayload.nonce,
        pkceCodeVerifier: statePayload.codeVerifier,
      });

      const claims = tokens.claims();
      const email = typeof claims?.email === "string" ? claims.email : undefined;
      if (!email) {
        return reply.code(400).send({ error: "sso_provider_missing_email" });
      }

      const existing = await deps.pool.query<{ id: string; organization_id: string }>(
        `SELECT id, organization_id FROM users WHERE lower(email) = lower($1)`,
        [email],
      );
      let userId: string;
      if (existing.rows[0]) {
        if (existing.rows[0].organization_id !== organizationId) {
          return reply.code(403).send({ error: "email_belongs_to_different_organization" });
        }
        userId = existing.rows[0].id;
      } else {
        const inserted = await deps.pool.query<{ id: string }>(
          `INSERT INTO users (organization_id, email, role) VALUES ($1, $2, 'member') RETURNING id`,
          [organizationId, email],
        );
        userId = inserted.rows[0]!.id;
      }

      await deps.pool.query(
        `INSERT INTO audit_events (event_type, actor, payload, "timestamp") VALUES ($1, $2, $3, now())`,
        ["sso_login", userId, JSON.stringify({ organizationId, ssoConnectionId: connection.id })],
      );

      const { token } = await createSession(deps.pool, userId, deps.ttlSeconds);
      reply.setCookie(deps.cookieName, token, deps.cookieOptions);

      return reply.redirect("/");
    },
  );
}
