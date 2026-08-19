import argon2 from "argon2";

/**
 * Argon2id (argon2's default) over bcrypt: it's the current OWASP-recommended
 * default and, unlike bcrypt, has no silent 72-byte input truncation.
 */
export async function hashPassword(plain: string): Promise<string> {
  return argon2.hash(plain);
}

/**
 * Never throws for a malformed/foreign hash string — that's an expected
 * "wrong password" outcome from the caller's perspective, not a 500.
 */
export async function verifyPassword(hash: string, plain: string): Promise<boolean> {
  try {
    return await argon2.verify(hash, plain);
  } catch {
    return false;
  }
}
