import { NextResponse } from "next/server";
import { authConfig } from "@/lib/auth/config";
import { setSession, clearSession } from "@/lib/auth/session";

export const dynamic = "force-dynamic";
const loginAttempts = new Map<string, { failures: number; windowStartMs: number; blockedUntilMs: number }>();
const MAX_STATE_ENTRIES = 2048;

function parseEnvInt(name: string, fallback: number, min: number, max: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const value = Number(raw);
  if (!Number.isInteger(value) || value < min || value > max) return fallback;
  return value;
}

function resolveRateLimitConfig() {
  return {
    maxAttempts: parseEnvInt("UI_LOGIN_MAX_ATTEMPTS", 5, 1, 20),
    windowMs: parseEnvInt("UI_LOGIN_WINDOW_SECONDS", 300, 5, 86_400) * 1000,
    lockMs: parseEnvInt("UI_LOGIN_LOCK_SECONDS", 300, 5, 86_400) * 1000,
  };
}

function requestKey(request: Request): string {
  const forwarded = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const realIp = request.headers.get("x-real-ip")?.trim();
  const userAgent = request.headers.get("user-agent")?.trim() ?? "unknown";
  return `${forwarded || realIp || "unknown"}|${userAgent.slice(0, 120)}`;
}

function cleanupAttempts(nowMs: number, windowMs: number, lockMs: number): void {
  for (const [key, state] of loginAttempts.entries()) {
    const staleWindow = nowMs - state.windowStartMs > windowMs * 2;
    const staleLock = state.blockedUntilMs > 0 && nowMs > state.blockedUntilMs + lockMs;
    if (staleWindow || staleLock) {
      loginAttempts.delete(key);
    }
  }
  if (loginAttempts.size <= MAX_STATE_ENTRIES) return;
  const extra = loginAttempts.size - MAX_STATE_ENTRIES;
  let removed = 0;
  for (const key of loginAttempts.keys()) {
    loginAttempts.delete(key);
    removed += 1;
    if (removed >= extra) break;
  }
}

function checkBlocked(key: string, nowMs: number): number {
  const state = loginAttempts.get(key);
  if (!state) return 0;
  if (state.blockedUntilMs <= nowMs) return 0;
  return Math.ceil((state.blockedUntilMs - nowMs) / 1000);
}

function recordFailure(key: string, nowMs: number, maxAttempts: number, windowMs: number, lockMs: number): number {
  const current = loginAttempts.get(key);
  let state = current;
  if (!state || nowMs - state.windowStartMs > windowMs) {
    state = { failures: 0, windowStartMs: nowMs, blockedUntilMs: 0 };
  }
  state.failures += 1;
  if (state.failures >= maxAttempts) {
    state.blockedUntilMs = nowMs + lockMs;
  }
  loginAttempts.set(key, state);
  if (state.blockedUntilMs > nowMs) {
    return Math.ceil((state.blockedUntilMs - nowMs) / 1000);
  }
  return 0;
}

function clearFailures(key: string): void {
  loginAttempts.delete(key);
}

export function __resetLoginRateLimitForTests(): void {
  if (process.env.NODE_ENV === "test") {
    loginAttempts.clear();
  }
}

export async function POST(request: Request) {
  try {
    const nowMs = Date.now();
    const { maxAttempts, windowMs, lockMs } = resolveRateLimitConfig();
    cleanupAttempts(nowMs, windowMs, lockMs);
    const key = requestKey(request);
    const retryAfterSec = checkBlocked(key, nowMs);
    if (retryAfterSec > 0) {
      await clearSession();
      return NextResponse.json(
        { ok: false, error: "Too many login attempts. Try again later.", retry_after_s: retryAfterSec },
        { status: 429, headers: { "Retry-After": String(retryAfterSec) } }
      );
    }

    const body = await request.json();
    const password = typeof body.password === "string" ? body.password : "";
    if (!password) {
      await clearSession();
      return NextResponse.json({ ok: false, error: "Missing password" }, { status: 400 });
    }
    if (!authConfig.checkPassword(password)) {
      const blockedForSec = recordFailure(key, nowMs, maxAttempts, windowMs, lockMs);
      await clearSession();
      if (blockedForSec > 0) {
        return NextResponse.json(
          { ok: false, error: "Too many login attempts. Try again later.", retry_after_s: blockedForSec },
          { status: 429, headers: { "Retry-After": String(blockedForSec) } }
        );
      }
      return NextResponse.json({ ok: false, error: "Invalid password" }, { status: 401 });
    }
    clearFailures(key);
    await setSession();
    return NextResponse.json({ ok: true });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: String((e as Error).message) },
      { status: 500 }
    );
  }
}
