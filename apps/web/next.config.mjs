const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxies /api/* to apps/api so the browser only ever talks to one
  // origin (this app). That makes the session cookie same-origin — no
  // SameSite=None/cross-site-cookie handling needed anywhere — and every
  // apps/web request (including the SSE stream) automatically carries it.
  // See docs/architecture/ACCESS-AND-LICENSING.md.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/:path*` }];
  },
};

export default nextConfig;
