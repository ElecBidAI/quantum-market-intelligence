"use client";

import type { CSSProperties } from "react";
import { useLocale } from "./LocaleProvider";

export default function LanguageSwitcher() {
  const { locale, setLocale } = useLocale();

  return (
    <div style={{ display: "flex", gap: "0.4rem", fontSize: "0.85rem" }}>
      <button type="button" onClick={() => setLocale("es")} style={buttonStyle(locale === "es")}>
        ES
      </button>
      <span style={{ color: "#ccc" }}>·</span>
      <button type="button" onClick={() => setLocale("en")} style={buttonStyle(locale === "en")}>
        EN
      </button>
    </div>
  );
}

function buttonStyle(active: boolean): CSSProperties {
  return {
    background: "none",
    border: "none",
    padding: 0,
    cursor: "pointer",
    fontWeight: active ? 700 : 400,
    color: active ? "#111" : "#888",
    textDecoration: active ? "underline" : "none",
  };
}
