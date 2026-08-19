import { generateKeyPairSync, randomBytes, randomUUID, sign as cryptoSign } from "node:crypto";
import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";
import type { QueryablePool } from "../src/db.js";
import { encryptSecret } from "../src/sso-crypto.js";
import { sessionCookieOptions } from "../src/session.js";
import type { SsoRouteDeps } from "../src/routes/sso.js";

const ENCRYPTION_KEY = randomBytes(32).toString("base64");
const ORG_ID = randomUUID();
const ISSUER = "https://idp.example.test";
const CLIENT_ID = "qmi-test-client";
const CLIENT_SECRET = "fake-client-secret";

/**
 * A minimal fake OIDC provider good enough to drive openid-client's real
 * discovery + Authorization Code Grant + ID-token-verification code paths
 * with zero real network calls (the `fetchImpl` is injected into
 * SsoRouteDeps, same idiom as `createSocket` in services/market-data).
 * Issues real RS256-signed ID tokens using a throwaway keypair, since
 * openid-client verifies the signature for real — there is no "skip
 * verification" mode to lean on.
 */
function fakeIdp() {
  const { publicKey, privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwk = { ...publicKey.export({ format: "jwk" }), kid: "test-key", use: "sig", alg: "RS256" };

  function base64url(input: Buffer | string): string {
    return Buffer.from(input).toString("base64url");
  }

  function signIdToken(claims: Record<string, unknown>): string {
    const header = { alg: "RS256", typ: "JWT", kid: "test-key" };
    const signingInput = `${base64url(JSON.stringify(header))}.${base64url(JSON.stringify(claims))}`;
    const signature = cryptoSign("RSA-SHA256", Buffer.from(signingInput), privateKey);
    return `${signingInput}.${base64url(signature).replace(/=+$/, "")}`;
  }

  let nextIdTokenClaims: Record<string, unknown> | null = null;
  function queueIdToken(claims: Record<string, unknown>): void {
    nextIdTokenClaims = claims;
  }

  const fetchImpl: typeof fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

    if (url === `${ISSUER}/.well-known/openid-configuration`) {
      return Response.json({
        issuer: ISSUER,
        authorization_endpoint: `${ISSUER}/authorize`,
        token_endpoint: `${ISSUER}/token`,
        jwks_uri: `${ISSUER}/jwks`,
        response_types_supported: ["code"],
        subject_types_supported: ["public"],
        id_token_signing_alg_values_supported: ["RS256"],
        token_endpoint_auth_methods_supported: ["client_secret_post", "client_secret_basic"],
      });
    }
    if (url === `${ISSUER}/jwks`) {
      return Response.json({ keys: [jwk] });
    }
    if (url === `${ISSUER}/token`) {
      if (!nextIdTokenClaims) throw new Error("fakeIdp: no ID token claims queued for this test");
      return Response.json({
        access_token: "fake-access-token",
        token_type: "Bearer",
        id_token: signIdToken(nextIdTokenClaims),
        expires_in: 3600,
      });
    }
    throw new Error(`fakeIdp: unhandled fetch to ${url} (init: ${JSON.stringify(init)})`);
  };

  return { fetchImpl, queueIdToken };
}

interface SsoConnectionRow {
  organization_id: string;
  issuer: string;
  client_id: string;
  client_secret_ciphertext: Buffer;
  client_secret_iv: Buffer;
  client_secret_tag: Buffer;
}
interface FakeUserRow {
  id: string;
  organization_id: string;
  email: string;
  role: "member" | "admin";
}

function fakeStore() {
  const encrypted = encryptSecret(CLIENT_SECRET, ENCRYPTION_KEY);
  const connection: SsoConnectionRow = {
    organization_id: ORG_ID,
    issuer: ISSUER,
    client_id: CLIENT_ID,
    client_secret_ciphertext: encrypted.ciphertext,
    client_secret_iv: encrypted.iv,
    client_secret_tag: encrypted.tag,
  };
  const users = new Map<string, FakeUserRow>();
  const auditEvents: { event_type: string; actor: string }[] = [];
  const sessions = new Map<string, string>();

  const pool: QueryablePool = {
    query: async (sql, params = []) => {
      if (sql.includes("FROM sso_connections")) {
        return { rows: [connection] };
      }
      if (sql.includes("SELECT id, organization_id FROM users")) {
        const [email] = params as [string];
        const found = [...users.values()].find((u) => u.email.toLowerCase() === email.toLowerCase());
        return { rows: found ? [found] : [] };
      }
      if (sql.includes("INSERT INTO users")) {
        const [organizationId, email] = params as [string, string];
        const id = randomUUID();
        users.set(id, { id, organization_id: organizationId, email, role: "member" });
        return { rows: [{ id }] };
      }
      if (sql.includes("INSERT INTO audit_events")) {
        const [eventType, actor] = params as [string, string];
        auditEvents.push({ event_type: eventType, actor });
        return { rows: [] };
      }
      if (sql.includes("INSERT INTO sessions")) {
        const [userId, tokenHash] = params as [string, string];
        sessions.set(tokenHash, userId);
        return { rows: [] };
      }
      throw new Error(`fakeStore: unhandled query: ${sql}`);
    },
  };

  return { pool, users, auditEvents, sessions };
}

function ssoDeps(pool: QueryablePool, fetchImpl: typeof fetch): SsoRouteDeps {
  return {
    pool,
    cookieName: "qmi_session",
    cookieOptions: sessionCookieOptions({ NODE_ENV: "test", SESSION_COOKIE_NAME: "qmi_session", SESSION_TTL_SECONDS: 3600 }),
    ttlSeconds: 3600,
    encryptionKey: ENCRYPTION_KEY,
    apiBaseUrl: "https://api.qmi.test",
    fetchImpl,
  };
}

describe("GET /auth/sso/:organizationId/start", () => {
  it("redirects to the IdP's authorization endpoint with state/nonce/PKCE params", async () => {
    const { pool } = fakeStore();
    const { fetchImpl } = fakeIdp();
    const app = buildApp({ sso: ssoDeps(pool, fetchImpl) });

    const res = await app.inject({ method: "GET", url: `/auth/sso/${ORG_ID}/start` });

    expect(res.statusCode).toBe(302);
    const location = new URL(res.headers.location as string);
    expect(location.origin).toBe(ISSUER);
    expect(location.searchParams.get("client_id")).toBe(CLIENT_ID);
    expect(location.searchParams.get("state")).toBeTruthy();
    expect(location.searchParams.get("nonce")).toBeTruthy();
    expect(location.searchParams.get("code_challenge_method")).toBe("S256");
    expect(res.cookies.some((c) => c.name === "qmi_sso_state")).toBe(true);

    await app.close();
  });

  it("404s when the organization has no SSO connection configured", async () => {
    const emptyPool: QueryablePool = { query: async () => ({ rows: [] }) };
    const { fetchImpl } = fakeIdp();
    const app = buildApp({ sso: ssoDeps(emptyPool, fetchImpl) });

    const res = await app.inject({ method: "GET", url: `/auth/sso/${randomUUID()}/start` });
    expect(res.statusCode).toBe(404);

    await app.close();
  });

  it("is not registered at all when sso deps are omitted", async () => {
    const app = buildApp();
    const res = await app.inject({ method: "GET", url: `/auth/sso/${ORG_ID}/start` });
    expect(res.statusCode).toBe(404);
    await app.close();
  });
});

describe("GET /auth/sso/:organizationId/callback", () => {
  it("400s when the state cookie is missing", async () => {
    const { pool } = fakeStore();
    const { fetchImpl } = fakeIdp();
    const app = buildApp({ sso: ssoDeps(pool, fetchImpl) });

    const res = await app.inject({ method: "GET", url: `/auth/sso/${ORG_ID}/callback?code=abc&state=xyz` });
    expect(res.statusCode).toBe(400);

    await app.close();
  });

  it("completes the grant, JIT-provisions a new user, and starts a session", async () => {
    const store = fakeStore();
    const idp = fakeIdp();
    const app = buildApp({ sso: ssoDeps(store.pool, idp.fetchImpl) });

    const startRes = await app.inject({ method: "GET", url: `/auth/sso/${ORG_ID}/start` });
    const location = new URL(startRes.headers.location as string);
    const state = location.searchParams.get("state")!;
    const nonce = location.searchParams.get("nonce")!;
    const stateCookie = startRes.cookies.find((c) => c.name === "qmi_sso_state")!.value;

    idp.queueIdToken({
      iss: ISSUER,
      sub: "idp-subject-1",
      aud: CLIENT_ID,
      exp: Math.floor(Date.now() / 1000) + 300,
      iat: Math.floor(Date.now() / 1000),
      nonce,
      email: "newuser@acme.test",
    });

    const callbackRes = await app.inject({
      method: "GET",
      url: `/auth/sso/${ORG_ID}/callback?code=fake-code&state=${state}`,
      headers: { cookie: `qmi_sso_state=${stateCookie}` },
    });

    expect(callbackRes.statusCode).toBe(302);
    expect(callbackRes.cookies.some((c) => c.name === "qmi_session")).toBe(true);
    expect([...store.users.values()].some((u) => u.email === "newuser@acme.test")).toBe(true);
    expect(store.auditEvents.some((e) => e.event_type === "sso_login")).toBe(true);

    await app.close();
  });

  it("reuses the existing user on a second SSO login instead of creating a duplicate", async () => {
    const store = fakeStore();
    const idp = fakeIdp();
    const app = buildApp({ sso: ssoDeps(store.pool, idp.fetchImpl) });

    async function ssoLoginOnce(): Promise<void> {
      const startRes = await app.inject({ method: "GET", url: `/auth/sso/${ORG_ID}/start` });
      const location = new URL(startRes.headers.location as string);
      const state = location.searchParams.get("state")!;
      const nonce = location.searchParams.get("nonce")!;
      const stateCookie = startRes.cookies.find((c) => c.name === "qmi_sso_state")!.value;

      idp.queueIdToken({
        iss: ISSUER,
        sub: "idp-subject-2",
        aud: CLIENT_ID,
        exp: Math.floor(Date.now() / 1000) + 300,
        iat: Math.floor(Date.now() / 1000),
        nonce,
        email: "repeat@acme.test",
      });

      const callbackRes = await app.inject({
        method: "GET",
        url: `/auth/sso/${ORG_ID}/callback?code=fake-code&state=${state}`,
        headers: { cookie: `qmi_sso_state=${stateCookie}` },
      });
      expect(callbackRes.statusCode).toBe(302);
    }

    await ssoLoginOnce();
    await ssoLoginOnce();

    const matching = [...store.users.values()].filter((u) => u.email === "repeat@acme.test");
    expect(matching).toHaveLength(1);

    await app.close();
  });
});
