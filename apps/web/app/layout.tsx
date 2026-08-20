import type { Metadata } from "next";
import type { ReactNode } from "react";
import { THEME } from "../lib/theme";
import LocaleProvider from "./LocaleProvider";

export const metadata: Metadata = {
  title: "QMI — Quantum Market Intelligence",
  description: "Phase 0 foundation build. No live trading capability.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body style={{ margin: 0, background: THEME.bg }}>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
