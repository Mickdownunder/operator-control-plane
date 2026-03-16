import { NextRequest, NextResponse } from "next/server";
import { execFile } from "child_process";
import { getSession } from "@/lib/auth/session";

const BRAIN = process.env.OPERATOR_ROOT
  ? `${process.env.OPERATOR_ROOT}/bin/brain`
  : `${process.env.HOME || "/root"}/operator/bin/brain`;
const TARGET_RE = /^[A-Za-z0-9_./-]{1,200}$/;

export const dynamic = "force-dynamic";

function parseGovernance(raw: unknown): number | null {
  const value =
    typeof raw === "number"
      ? raw
      : typeof raw === "string" && raw.trim() !== ""
        ? Number(raw)
        : Number.NaN;
  if (!Number.isInteger(value) || value < 0 || value > 3) return null;
  return value;
}

function parseTarget(raw: unknown): string | null {
  if (raw === undefined || raw === null) return "";
  if (typeof raw !== "string") return null;
  const value = raw.trim();
  if (!value) return "";
  if (!TARGET_RE.test(value)) return null;
  if (value.includes("..")) return null;
  return value;
}

async function runBrain(args: string[], timeout: number): Promise<string> {
  return await new Promise<string>((resolve, reject) => {
    execFile(BRAIN, args, { timeout, maxBuffer: 1024 * 1024 }, (error, stdout) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(stdout);
    });
  });
}

export async function POST(req: NextRequest) {
  const ok = await getSession();
  if (!ok)
    return NextResponse.json({ ok: false, error: "Unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const governance = parseGovernance(body.governance ?? 2);
  if (governance === null) {
    return NextResponse.json(
      { ok: false, error: "Invalid governance level (allowed: 0-3)" },
      { status: 400 }
    );
  }
  const target = parseTarget(body.target ?? "");
  if (target === null) {
    return NextResponse.json(
      { ok: false, error: "Invalid target format" },
      { status: 400 }
    );
  }

  const args = ["plumber", "--governance", String(governance)];
  if (target) args.push("--target", target);

  try {
    const stdout = await runBrain(args, 30_000);
    const report = JSON.parse(stdout);
    return NextResponse.json({ ok: true, report });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  const ok = await getSession();
  if (!ok)
    return NextResponse.json({ ok: false, error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(req.url);
  const view = searchParams.get("view");

  try {
    if (view === "fingerprints") {
      const stdout = await runBrain(["plumber", "--fingerprints"], 10_000);
      return NextResponse.json({ ok: true, fingerprints: JSON.parse(stdout) });
    }

    const stdout = await runBrain(["plumber", "--list-patches"], 10_000);
    const data = JSON.parse(stdout);
    return NextResponse.json({ ok: true, ...data });
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    return NextResponse.json({ ok: false, error: msg }, { status: 500 });
  }
}
