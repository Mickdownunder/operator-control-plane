import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { OPERATOR_ROOT } from "../runner";

const researchProjectIdRe = /^proj-[a-zA-Z0-9-]+$/;
const AGENT_ROOT = process.env.AGENT_ROOT ?? "/root/agent/workspace";
const JUNE_HANDOFF = process.env.JUNE_CONTROL_PLANE_HANDOFF_BIN ?? join(AGENT_ROOT, "bin", "june-control-plane-handoff");

function validateProjectId(id: string): string | null {
  const s = (id || "").trim().split(/\s+/)[0];
  return s && researchProjectIdRe.test(s) ? s : null;
}

function runJuneHandoff(args: string[], timeoutMs = 180_000): Record<string, unknown> {
  const raw = execFileSync("python3", [JUNE_HANDOFF, ...args], {
    encoding: "utf8",
    timeout: timeoutMs,
    env: { ...process.env, OPERATOR_ROOT },
  }).trim();
  return raw ? JSON.parse(raw) as Record<string, unknown> : {};
}

export function registerResearch(api: { registerCommand: (c: unknown) => void }) {
  api.registerCommand({
    name: "research-feedback",
    description: "Send feedback for a research project. Usage: /research-feedback <project_id> <dig_deeper|wrong|excellent|ignore> [comment]. Or: /research-feedback <project_id> redirect \"new question\"",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx: { args?: string }) => {
      const raw = (ctx.args || "").trim();
      if (!raw) return { text: "Usage: /research-feedback <project_id> <type> [comment]\ntype: dig_deeper | wrong | excellent | ignore | redirect" };
      try {
        const parts = raw.split(/\s+/);
        const projectId = parts[0] || "";
        const fbType = parts[1] || "";
        const comment = parts.slice(2).join(" ");
        const feedbackScript = join(OPERATOR_ROOT, "tools", "research_feedback.py");
        const args = comment
          ? [feedbackScript, projectId, fbType, comment]
          : [feedbackScript, projectId, fbType];
        const out = execFileSync("python3", args, {
          encoding: "utf8",
          timeout: 15_000,
          env: { ...process.env, OPERATOR_ROOT },
        }).trim();
        const data = JSON.parse(out) as { ok?: boolean; type?: string };
        if (data.ok) {
          return { text: `Feedback recorded: ${data.type}${data.type === "redirect" ? " (question added)" : ""}.` };
        }
        return { text: out };
      } catch (e: unknown) {
        return { text: `Feedback failed: ${(e as Error).message}` };
      }
    },
  });

  api.registerCommand({
    name: "research-start",
    description: "Start a new research project under June autopilot. Usage: /research-start <question>",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx: { args?: string }) => {
      const question = (ctx.args || "").trim();
      if (!question) return { text: "Usage: /research-start <question>\nExample: /research-start What is the current state of solid-state batteries?" };
      try {
        const payload = runJuneHandoff([
          "ui-research-start",
          "--question",
          question,
          "--research-mode",
          "standard",
          "--run-until-done",
          "1",
        ]);
        const projectId = typeof payload.projectId === "string" ? payload.projectId : "";
        if (!projectId) throw new Error("No project_id returned by June handoff.");
        return {
          text: `Project created: ${projectId}\nJune will continue this research mission under autopilot.\n\nOnly resume manually for pause, review, or recovery: /research-cycle ${projectId}\nStatus: /research-status ${projectId}`,
        };
      } catch (e: unknown) {
        return { text: `research-start failed: ${(e as Error).message}` };
      }
    },
  });

  api.registerCommand({
    name: "research-cycle",
    description: "Resume June-managed research autopilot for an existing project. Usage: /research-cycle <project_id>",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx: { args?: string }) => {
      const projectId = validateProjectId(ctx.args || "");
      if (!projectId) return { text: "Usage: /research-cycle <project_id>\nExample: /research-cycle proj-20260225-654f85b2" };
      try {
        runJuneHandoff(["ui-research-continue", "--project-id", projectId], 30_000);
        return {
          text: `June autopilot resumed for existing project.\nProject: ${projectId}\nStatus: /research-status ${projectId}`,
        };
      } catch (e: unknown) {
        return { text: `research-cycle failed: ${(e as Error).message}` };
      }
    },
  });

  api.registerCommand({
    name: "research-go",
    description: "Start research; runs one cycle every 6h for up to 14 days (background). Usage: /research-go <question>",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx: { args?: string }) => {
      const question = (ctx.args || "").trim();
      if (!question) return { text: "Usage: /research-go <question>\nExample: /research-go What is the current state of solid-state batteries?" };
      try {
        const payload = runJuneHandoff([
          "research-start",
          "--question",
          question,
          "--research-mode",
          "standard",
          "--run-until-done",
          "0",
          "--source-command",
          "research-go",
        ]);
        const projectId = typeof payload.projectId === "string" ? payload.projectId.trim() : "";
        if (!projectId) throw new Error("No project_id found in artifacts.");
        const { spawn } = await import("node:child_process");
        const script = join(OPERATOR_ROOT, "tools", "run-research-over-days.sh");
        const env = {
          ...process.env,
          OPERATOR_ROOT,
          PATH: [join(OPERATOR_ROOT, "bin"), process.env.PATH].filter(Boolean).join(":"),
        };
        spawn("bash", [script, projectId, "6", "14"], {
          cwd: OPERATOR_ROOT,
          detached: true,
          stdio: "ignore",
          env,
        }).unref();
        return {
          text: `Research started and will continue in the background over multiple days.\nProject: ${projectId}\nOne cycle every 6h, maximum 14 days.\n\nStatus: /research-status ${projectId}\nLog: research/${projectId}/over-days.log`,
        };
      } catch (e: unknown) {
        return { text: `research-go failed: ${(e as Error).message}` };
      }
    },
  });

  api.registerCommand({
    name: "research-status",
    description: "Show research project status. Usage: /research-status <project_id>",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx: { args?: string }) => {
      const projectId = validateProjectId(ctx.args || "");
      if (!projectId) return { text: "Usage: /research-status <project_id>" };
      try {
        const projectPath = join(OPERATOR_ROOT, "research", projectId, "project.json");
        if (!existsSync(projectPath)) return { text: `Project not found: ${projectId}` };
        const data = JSON.parse(readFileSync(projectPath, "utf8")) as { phase?: string; status?: string; question?: string };
        const phase = data.phase || "?";
        const status = data.status || "?";
        const question = (data.question || "").slice(0, 60) + ((data.question || "").length > 60 ? "…" : "");
        let reports = "";
        try {
          const reportsDir = join(OPERATOR_ROOT, "research", projectId, "reports");
          if (existsSync(reportsDir)) {
            const files = readdirSync(reportsDir).filter((f: string) => f.endsWith(".md"));
            reports = `Reports: ${files.length}`;
          }
        } catch {
          // ignore
        }
        return {
          text: `Project: ${projectId}\nQuestion: ${question}\nPhase: ${phase}\nStatus: ${status}\n${reports}`,
        };
      } catch (e: unknown) {
        return { text: `status failed: ${(e as Error).message}` };
      }
    },
  });
}
