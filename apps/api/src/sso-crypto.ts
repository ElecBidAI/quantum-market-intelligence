import { createCipheriv, createDecipheriv, randomBytes } from "node:crypto";

/**
 * AES-256-GCM encryption for SSO client secrets at rest
 * (docs/architecture/ACCESS-AND-LICENSING.md). Pure functions — no Fastify
 * or DB dependency, independently testable.
 */

const ALGORITHM = "aes-256-gcm";
const IV_LENGTH_BYTES = 12;

export interface EncryptedSecret {
  ciphertext: Buffer;
  iv: Buffer;
  tag: Buffer;
}

function decodeKey(key: string): Buffer {
  const decoded = Buffer.from(key, "base64");
  if (decoded.length !== 32) {
    throw new Error("AUTH_ENCRYPTION_KEY must decode to exactly 32 bytes (base64-encoded)");
  }
  return decoded;
}

export function encryptSecret(plain: string, key: string): EncryptedSecret {
  const iv = randomBytes(IV_LENGTH_BYTES);
  const cipher = createCipheriv(ALGORITHM, decodeKey(key), iv);
  const ciphertext = Buffer.concat([cipher.update(plain, "utf8"), cipher.final()]);
  return { ciphertext, iv, tag: cipher.getAuthTag() };
}

/**
 * Throws if `key` is wrong or if `ciphertext`/`iv`/`tag` were tampered with
 * — GCM's authentication tag makes corruption an explicit failure, never a
 * silently-wrong plaintext.
 */
export function decryptSecret(encrypted: EncryptedSecret, key: string): string {
  const decipher = createDecipheriv(ALGORITHM, decodeKey(key), encrypted.iv);
  decipher.setAuthTag(encrypted.tag);
  const plaintext = Buffer.concat([decipher.update(encrypted.ciphertext), decipher.final()]);
  return plaintext.toString("utf8");
}
