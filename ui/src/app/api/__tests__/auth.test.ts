import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/auth/config", () => ({
  authConfig: {
    checkPassword: vi.fn(),
  },
}));
vi.mock("@/lib/auth/session", () => ({
  setSession: vi.fn(),
  clearSession: vi.fn(),
}));

describe("API auth login route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.UI_LOGIN_MAX_ATTEMPTS = "5";
    process.env.UI_LOGIN_WINDOW_SECONDS = "300";
    process.env.UI_LOGIN_LOCK_SECONDS = "300";
  });

  it("POST returns 400 when password missing", async () => {
    const { POST } = await import("@/app/api/auth/login/route");
    const res = await POST(
      new Request("http://x", {
        method: "POST",
        body: JSON.stringify({}),
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.ok).toBe(false);
    expect(json.error).toContain("password");
  });

  it("POST returns 401 when password invalid", async () => {
    const { authConfig } = await import("@/lib/auth/config");
    vi.mocked(authConfig.checkPassword).mockReturnValueOnce(false);
    const { POST } = await import("@/app/api/auth/login/route");
    const res = await POST(
      new Request("http://x", {
        method: "POST",
        body: JSON.stringify({ password: "wrong" }),
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.ok).toBe(false);
  });

  it("POST returns 200 when password valid", async () => {
    const { authConfig } = await import("@/lib/auth/config");
    vi.mocked(authConfig.checkPassword).mockReturnValueOnce(true);
    const { POST } = await import("@/app/api/auth/login/route");
    const res = await POST(
      new Request("http://x", {
        method: "POST",
        body: JSON.stringify({ password: "correct" }),
        headers: { "Content-Type": "application/json" },
      })
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
  });

  it("POST rate-limits repeated invalid password attempts", async () => {
    process.env.UI_LOGIN_MAX_ATTEMPTS = "2";
    process.env.UI_LOGIN_WINDOW_SECONDS = "600";
    process.env.UI_LOGIN_LOCK_SECONDS = "600";
    const { authConfig } = await import("@/lib/auth/config");
    const { POST, __resetLoginRateLimitForTests } = await import("@/app/api/auth/login/route");
    __resetLoginRateLimitForTests();
    vi.mocked(authConfig.checkPassword).mockReturnValue(false);

    const req = () =>
      new Request("http://x", {
        method: "POST",
        body: JSON.stringify({ password: "wrong" }),
        headers: {
          "Content-Type": "application/json",
          "x-forwarded-for": "203.0.113.9",
          "user-agent": "vitest-auth",
        },
      });

    const first = await POST(req());
    expect(first.status).toBe(401);
    const second = await POST(req());
    expect(second.status).toBe(429);
    const json = await second.json();
    expect(json.ok).toBe(false);
    expect(json.error).toContain("Too many");
  });
});
