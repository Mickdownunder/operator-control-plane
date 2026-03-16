import { describe, it, expect, vi, beforeEach } from "vitest";
import crypto from "crypto";

describe("auth config", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    process.env.NODE_ENV = "test";
  });

  it("checkPassword returns false when UI_PASSWORD_HASH not set", async () => {
    const orig = process.env.UI_PASSWORD_HASH;
    delete process.env.UI_PASSWORD_HASH;
    const { authConfig } = await import("../config");
    expect(authConfig.checkPassword("any")).toBe(false);
    if (orig !== undefined) process.env.UI_PASSWORD_HASH = orig;
  });

  it("checkPassword returns false for empty password when hash set", async () => {
    const orig = process.env.UI_PASSWORD_HASH;
    process.env.UI_PASSWORD_HASH = "a".repeat(64);
    const { authConfig } = await import("../config");
    expect(authConfig.checkPassword("")).toBe(false);
    if (orig !== undefined) process.env.UI_PASSWORD_HASH = orig;
    else delete process.env.UI_PASSWORD_HASH;
  });

  it("checkPassword returns true for valid legacy sha256 hash", async () => {
    const orig = process.env.UI_PASSWORD_HASH;
    process.env.UI_PASSWORD_HASH = crypto.createHash("sha256").update("correct", "utf8").digest("hex");
    const { authConfig } = await import("../config");
    expect(authConfig.checkPassword("correct")).toBe(true);
    expect(authConfig.checkPassword("wrong")).toBe(false);
    if (orig !== undefined) process.env.UI_PASSWORD_HASH = orig;
    else delete process.env.UI_PASSWORD_HASH;
  });

  it("checkPassword returns true for valid scrypt hash", async () => {
    const orig = process.env.UI_PASSWORD_HASH;
    const salt = Buffer.from("0123456789abcdef0123456789abcdef", "hex");
    const derived = crypto.scryptSync("correct", salt, 64, { N: 16384, r: 8, p: 1, maxmem: 128 * 16384 * 8 + 1024 * 1024 });
    process.env.UI_PASSWORD_HASH = `scrypt$16384$8$1$${salt.toString("hex")}$${derived.toString("hex")}`;
    const { authConfig } = await import("../config");
    expect(authConfig.checkPassword("correct")).toBe(true);
    expect(authConfig.checkPassword("wrong")).toBe(false);
    if (orig !== undefined) process.env.UI_PASSWORD_HASH = orig;
    else delete process.env.UI_PASSWORD_HASH;
  });

  it("createToken returns string with three parts", async () => {
    const { authConfig } = await import("../config");
    const token = authConfig.createToken();
    expect(typeof token).toBe("string");
    expect(token.split(".").length).toBe(3);
  });

  it("verifyToken returns true for freshly created token", async () => {
    const { authConfig } = await import("../config");
    const token = authConfig.createToken();
    expect(authConfig.verifyToken(token)).toBe(true);
  });

  it("verifyToken returns false for invalid token", async () => {
    const { authConfig } = await import("../config");
    // Use same-length hex to avoid timingSafeEqual buffer length throw
    expect(authConfig.verifyToken("0.0." + "0".repeat(64))).toBe(false);
  });

  it("createToken throws when session secret is missing outside tests", async () => {
    const origNodeEnv = process.env.NODE_ENV;
    const origSecret = process.env.UI_SESSION_SECRET;
    process.env.NODE_ENV = "production";
    delete process.env.UI_SESSION_SECRET;
    vi.resetModules();
    const { authConfig } = await import("../config");
    expect(() => authConfig.createToken()).toThrow("UI_SESSION_SECRET must be set");
    process.env.NODE_ENV = origNodeEnv;
    if (origSecret !== undefined) process.env.UI_SESSION_SECRET = origSecret;
    else delete process.env.UI_SESSION_SECRET;
  });
});
