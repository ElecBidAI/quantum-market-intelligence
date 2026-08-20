import type { Metadata } from "next";
import type { ReactNode } from "react";
import LocaleProvider from "./LocaleProvider";

export const metadata: Metadata = {
  title: "QMI — Quantum Market Intelligence",
  description: "Phase 0 foundation build. No live trading capability.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es">
      <body>
        <LocaleProvider>{children}</LocaleProvider>
      </body>
    </html>
  );
}
