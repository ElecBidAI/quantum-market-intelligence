/**
 * Every apps/api call goes through the same-origin `/api` prefix, proxied
 * to the real API by next.config.mjs's rewrites() (see
 * docs/architecture/ACCESS-AND-LICENSING.md). Same-origin means the
 * session cookie is sent automatically — no `credentials: "include"` or
 * manual header wiring needed here or at any call site.
 */
export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`/api${path}`, init);
}

export function apiStreamUrl(path: string): string {
  return `/api${path}`;
}
