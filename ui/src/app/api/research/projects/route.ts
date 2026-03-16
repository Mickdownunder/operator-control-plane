import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth/session";
import { listResearchProjects } from "@/lib/operator/research";
import { submitResearchStartIntent } from "@/lib/operator/actions";

export const dynamic = "force-dynamic";

export async function GET() {
  const ok = await getSession();
  if (!ok) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  try {
    const projects = await listResearchProjects();
    return NextResponse.json({ projects });
  } catch (e) {
    return NextResponse.json(
      { error: String((e as Error).message) },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  const ok = await getSession();
  if (!ok) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  try {
    const body = await request.json();
    const question = typeof body.question === "string" ? body.question.trim() : "";
    if (!question) {
      return NextResponse.json(
        { ok: false, error: "question is required" },
        { status: 400 }
      );
    }
    const validModes = ["standard", "frontier", "discovery"];
    const researchMode = validModes.includes(body.research_mode) ? body.research_mode : "standard";
    const runUntilDone = body.run_until_done !== false;
    const result = await submitResearchStartIntent(question, researchMode, runUntilDone);
    if (!result.ok) {
      return NextResponse.json(
        { ok: false, error: result.error ?? "workflow failed" },
        { status: 400 }
      );
    }
    return NextResponse.json({
      ok: true,
      jobId: result.jobId,
      projectId: result.projectId,
      requestEventId: result.requestEventId,
      message: runUntilDone
        ? "Project created. All phases continue automatically and the report appears when the run completes."
        : "Project created. Further execution continues through the canonical control-plane path.",
    });
  } catch (e) {
    return NextResponse.json(
      { ok: false, error: String((e as Error).message) },
      { status: 500 }
    );
  }
}
