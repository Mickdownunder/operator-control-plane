/**
 * Auth config. Password hash stored server-side only.
 * Set UI_PASSWORD_HASH in env.
 * Preferred format: scrypt$N$r$p$salt_hex$hash_hex
 * Legacy format: SHA-256 hex (still accepted for backwards compatibility).
 * The login route enforces rate limiting/lockout via UI_LOGIN_* env vars.
 * For internet-facing deployments, prefer the scrypt format.
 */
import crypto from "crypto";

const SESSION_COOKIE = "operator_session";
const SESSION_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

function resolveSessionSecret(): string | null {
  const raw = process.env.UI_SESSION_SECRET?.trim();
  if (raw && raw !== "change-me-in-production") return raw;
  if (process.env.NODE_ENV === "test") {
    return "test-session-secret-do-not-use-in-production";
  }
  return null;
}

const SESSION_SECRET = resolveSessionSecret();

function verifyLegacySha256(raw: string, password: string): boolean {
  if (raw.length !== 64 || !/^[a-fA-F0-9]{64}$/.test(raw)) return false;
  const inputHash = crypto.createHash("sha256").update(password, "utf8").digest("hex");
  try {
    const bufHash = Buffer.from(raw, "hex");
    const bufInput = Buffer.from(inputHash, "hex");
    if (bufHash.length !== 32 || bufInput.length !== 32) return false;
    return crypto.timingSafeEqual(bufHash, bufInput);
  } catch {
    return false;
  }
}

function verifyScrypt(raw: string, password: string): boolean {
  const parts = raw.split("$");
  if (parts.length !== 6 || parts[0] !== "scrypt") return false;
  const [, nRaw, rRaw, pRaw, saltHex, hashHex] = parts;
  const N = Number(nRaw);
  const r = Number(rRaw);
  const p = Number(pRaw);
  if (
    !Number.isInteger(N) || !Number.isInteger(r) || !Number.isInteger(p) ||
    N < 2 || r < 1 || p < 1 || !/^[a-fA-F0-9]+$/.test(saltHex) || !/^[a-fA-F0-9]+$/.test(hashHex)
  ) {
    return false;
  }
  try {
    const salt = Buffer.from(saltHex, "hex");
    const expected = Buffer.from(hashHex, "hex");
    if (!salt.length || !expected.length) return false;
    const derived = crypto.scryptSync(password, salt, expected.length, {
      N,
      r,
      p,
      maxmem: 128 * N * r + 1024 * 1024,
    });
    return crypto.timingSafeEqual(derived, expected);
  } catch {
    return false;
  }
}

export const authConfig = {
  SESSION_COOKIE,
  SESSION_MAX_AGE,
  SESSION_SECRET,
  /** Compare password with env UI_PASSWORD_HASH. Prefer scrypt$...; legacy SHA-256 hex is still accepted. */
  checkPassword(password: string): boolean {
    const raw = process.env.UI_PASSWORD_HASH?.trim();
    if (!raw || !password) return false;
    if (raw.startsWith("scrypt$")) return verifyScrypt(raw, password);
    return verifyLegacySha256(raw, password);
  },
  /** Create a session token (HMAC of timestamp + random). */
  createToken(): string {
    if (!SESSION_SECRET) {
      throw new Error("UI_SESSION_SECRET must be set before creating sessions");
    }
    const payload = `${Date.now()}.${crypto.randomBytes(16).toString("hex")}`;
    const sig = crypto.createHmac("sha256", SESSION_SECRET).update(payload).digest("hex");
    return `${payload}.${sig}`;
  },
  verifyToken(token: string): boolean {
    if (!SESSION_SECRET) return false;
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    const [ts, , sig] = parts;
    if (sig.length !== 64) return false;
    const expected = crypto.createHmac("sha256", SESSION_SECRET).update(`${parts[0]}.${parts[1]}`).digest("hex");
    if (!crypto.timingSafeEqual(Buffer.from(sig, "hex"), Buffer.from(expected, "hex"))) return false;
    const age = Date.now() - Number(ts);
    return age >= 0 && age < SESSION_MAX_AGE * 1000;
  },
};
