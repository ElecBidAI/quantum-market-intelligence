import { randomBytes } from "node:crypto";
import { describe, expect, it } from "vitest";
import { decryptSecret, encryptSecret } from "../src/sso-crypto.js";

const KEY = randomBytes(32).toString("base64");
const OTHER_KEY = randomBytes(32).toString("base64");

describe("encryptSecret / decryptSecret", () => {
  it("round-trips a secret", () => {
    const encrypted = encryptSecret("super-secret-client-secret", KEY);
    expect(decryptSecret(encrypted, KEY)).toBe("super-secret-client-secret");
  });

  it("never stores the plaintext in the ciphertext bytes", () => {
    const encrypted = encryptSecret("super-secret-client-secret", KEY);
    expect(encrypted.ciphertext.toString("utf8")).not.toContain("super-secret-client-secret");
  });

  it("uses a different IV on each call", () => {
    const a = encryptSecret("same-plaintext", KEY);
    const b = encryptSecret("same-plaintext", KEY);
    expect(a.iv.equals(b.iv)).toBe(false);
  });

  it("throws on decryption with the wrong key", () => {
    const encrypted = encryptSecret("super-secret-client-secret", KEY);
    expect(() => decryptSecret(encrypted, OTHER_KEY)).toThrow();
  });

  it("throws when the ciphertext has been tampered with", () => {
    const encrypted = encryptSecret("super-secret-client-secret", KEY);
    const tampered = { ...encrypted, ciphertext: Buffer.concat([encrypted.ciphertext.subarray(1), Buffer.from([0])]) };
    expect(() => decryptSecret(tampered, KEY)).toThrow();
  });

  it("throws when the auth tag has been tampered with", () => {
    const encrypted = encryptSecret("super-secret-client-secret", KEY);
    const tamperedTag = Buffer.from(encrypted.tag);
    tamperedTag[0] = tamperedTag[0]! ^ 0xff;
    expect(() => decryptSecret({ ...encrypted, tag: tamperedTag }, KEY)).toThrow();
  });

  it("rejects a key that doesn't decode to 32 bytes", () => {
    expect(() => encryptSecret("x", Buffer.from("too-short").toString("base64"))).toThrow(/32 bytes/);
  });
});
