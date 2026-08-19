import { describe, expect, it } from "vitest";
import { hashPassword, verifyPassword } from "../src/password.js";

describe("hashPassword / verifyPassword", () => {
  it("round-trips a correct password", async () => {
    const hash = await hashPassword("correct-horse-battery-staple");
    expect(await verifyPassword(hash, "correct-horse-battery-staple")).toBe(true);
  });

  it("rejects an incorrect password", async () => {
    const hash = await hashPassword("correct-horse-battery-staple");
    expect(await verifyPassword(hash, "wrong-password")).toBe(false);
  });

  it("never stores the plaintext password in the hash", async () => {
    const hash = await hashPassword("correct-horse-battery-staple");
    expect(hash).not.toContain("correct-horse-battery-staple");
  });

  it("resolves false (does not throw) for a malformed stored hash", async () => {
    await expect(verifyPassword("not-a-real-argon2-hash", "anything")).resolves.toBe(false);
  });
});
