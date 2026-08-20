"use client";

import { useState, type CSSProperties, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api-client";
import { THEME, FONT_FAMILY } from "../../lib/theme";
import { useLocale } from "../LocaleProvider";

export default function LoginPage() {
  const router = useRouter();
  const { t } = useLocale();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        router.push("/");
      } else {
        setError(t("login.error"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={mainStyle}>
      <form onSubmit={handleSubmit} style={cardStyle}>
        <h1 style={headingStyle}>{t("login.heading")}</h1>
        <label style={labelStyle}>
          {t("login.email")}
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={inputStyle}
          />
        </label>
        <label style={labelStyle}>
          {t("login.password")}
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
          />
        </label>
        {error && <p style={errorStyle}>{error}</p>}
        <button type="submit" disabled={submitting} style={submitButtonStyle}>
          {submitting ? t("login.submitting") : t("login.submit")}
        </button>
        <p style={footerTextStyle}>
          {t("login.noAccount")}{" "}
          <a href="/register" style={linkStyle}>
            {t("login.registerLink")}
          </a>
        </p>
      </form>
    </main>
  );
}

const mainStyle: CSSProperties = {
  fontFamily: FONT_FAMILY,
  background: THEME.bg,
  minHeight: "100vh",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "1rem",
};

const cardStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.9rem",
  width: "100%",
  maxWidth: 360,
  background: THEME.panelBg,
  border: `1px solid ${THEME.border}`,
  borderRadius: 8,
  padding: "1.75rem",
};

const headingStyle: CSSProperties = { margin: 0, color: THEME.textPrimary, fontSize: "1.3rem" };

const labelStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const inputStyle: CSSProperties = {
  display: "block",
  width: "100%",
  padding: "0.5rem 0.6rem",
  marginTop: "0.3rem",
  background: THEME.panelBgAlt,
  border: `1px solid ${THEME.border}`,
  borderRadius: 4,
  color: THEME.textPrimary,
  fontSize: "0.95rem",
};

const submitButtonStyle: CSSProperties = {
  background: THEME.accent,
  color: THEME.accentText,
  border: "none",
  borderRadius: 4,
  padding: "0.55rem",
  fontWeight: 600,
  cursor: "pointer",
};

const errorStyle: CSSProperties = { color: THEME.negative, fontSize: "0.85rem", margin: 0 };

const footerTextStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem", margin: 0 };

const linkStyle: CSSProperties = { color: THEME.link };
