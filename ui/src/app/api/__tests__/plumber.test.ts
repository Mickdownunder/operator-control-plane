import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth/session", () => ({
  getSession: vi.fn(),
}));
vi.mock("child_process", () => {
  const execFile = vi.fn();
  return {
    default: { execFile },
    execFile,
  };
});

describe("API plumber route", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { getSession } = await import("@/lib/auth/session");
    vi.mocked(getSession).mockResolvedValue(true);
  });

  it("POST rejects invalid target format", async () => {
    const { execFile } = await import("child_process");
    const { POST } = await import("@/app/api/actions/plumber/route");
    const request = new Request("http://localhost/api/actions/plumber", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ governance: 2, target: "foo; rm -rf /" }),
    });

    const res = await POST(request as never);
    const json = await res.json();

    expect(res.status).toBe(400);
    expect(json.ok).toBe(false);
    expect(json.error).toContain("target");
    expect(vi.mocked(execFile)).not.toHaveBeenCalled();
  });

  it("POST rejects invalid governance value", async () => {
    const { execFile } = await import("child_process");
    const { POST } = await import("@/app/api/actions/plumber/route");
    const request = new Request("http://localhost/api/actions/plumber", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ governance: 99 }),
    });

    const res = await POST(request as never);
    const json = await res.json();

    expect(res.status).toBe(400);
    expect(json.ok).toBe(false);
    expect(json.error).toContain("governance");
    expect(vi.mocked(execFile)).not.toHaveBeenCalled();
  });
});
