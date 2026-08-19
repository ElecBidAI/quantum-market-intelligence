"use client";

import { useState, type CSSProperties, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "../../lib/api-client";

export default function RegisterPage() {
  const router = useRouter();
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, organizationName }),
      });
      if (res.ok) {
        router.push("/");
      } else if (res.status === 409) {
        setError("An account with that email already exists.");
      } else {
        setError("Could not register. Check your details and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: 360 }}>
      <h1>Create your organization</h1>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        <label>
          Organization name
          <input
            type="text"
            required
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            style={inputStyle}
          />
        </label>
        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={inputStyle}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={inputStyle}
          />
        </label>
        {error && <p style={{ color: "#b00020" }}>{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p>
        Already have an account? <a href="/login">Log in</a>
      </p>
    </main>
  );
}

const inputStyle: CSSProperties = { display: "block", width: "100%", padding: "0.4rem", marginTop: "0.25rem" };
