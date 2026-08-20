"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../lib/api-client";
import { useLocale } from "./LocaleProvider";

/**
 * Minimal client-side session gate: checks GET /auth/me on mount and
 * redirects to /login if unauthenticated. Deliberately not a full
 * auth-context/provider — nothing else in this app needs the session
 * object yet, just a yes/no gate in front of the dashboard.
 */
export default function AuthGate({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { t } = useLocale();
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch("/auth/me")
      .then((res) => {
        if (cancelled) return;
        if (res.ok) {
          setAuthenticated(true);
        } else {
          router.push("/login");
        }
      })
      .catch(() => {
        if (!cancelled) router.push("/login");
      });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (!authenticated) {
    return <p style={{ color: "#666" }}>{t("authGate.checking")}</p>;
  }
  return <>{children}</>;
}
