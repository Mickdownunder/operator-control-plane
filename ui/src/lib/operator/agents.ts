import { readFile, readdir } from "fs/promises";
import path from "path";
import { OPERATOR_ROOT } from "./config";

/** Agent identity from workspace IDENTITY.md; OpenClaw agent slots; Operator workflows */
const AGENT_WORKSPACE = process.env.AGENT_WORKSPACE ?? "/root/agent/workspace";

export interface AgentInfo {
  id: string;
  name: string;
  description?: string;
  source: "openclaw" | "workflow" | "subagent";
  details?: string;
  /** Where the agent runs (for example "Server" for June). */
  location?: string;
  /** For sub-agents: ID of the delegating agent (June -> ARGUS -> ATLAS). */
  delegationFrom?: string;
}

/** Human-readable names and short descriptions for operator workflows */
const WORKFLOW_LABELS: Record<string, { name: string; desc: string }> = {
  planner: { name: "Planner", desc: "Plans next steps (LLM)" },
  critic: { name: "Critic", desc: "Evaluates system output (LLM)" },
  prioritize: { name: "Prioritize", desc: "Sets priorities" },
  "autopilot-infra": { name: "Autopilot Infra", desc: "Monitors infrastructure and starts cycles" },
  "tool-idea": { name: "Tool Idea", desc: "Proposes new tools (LLM)" },
  "tool-eval": { name: "Tool Eval", desc: "Evaluates tools (LLM)" },
  "tool-create": { name: "Tool Create", desc: "Creates tool script" },
  "tool-register": { name: "Tool Register", desc: "Registers tool" },
  "tool-use": { name: "Tool Use", desc: "Executes tool" },
  "tool-improve": { name: "Tool Improve", desc: "Improves tool" },
  "tool-backlog-add": { name: "Tool Backlog Add", desc: "Adds backlog entry" },
  "tool-backlog-improve": { name: "Tool Backlog Improve", desc: "Improves backlog" },
  signals: { name: "Signals", desc: "Collects system signals (disk, load)" },
  "infra-status": { name: "Infra Status", desc: "Infrastructure status check" },
  "propose-infra": { name: "Propose Infra", desc: "Infrastructure proposals" },
  "knowledge-commit": { name: "Knowledge Commit", desc: "Writes to the knowledge base" },
  "goal-progress": { name: "Goal Progress", desc: "Tracks progress against goals" },
  "product-spec": { name: "Product Spec", desc: "Creates product spec" },
  "product-skeleton": { name: "Product Skeleton", desc: "Creates product scaffold" },
  "product-feature-jobs": { name: "Product Feature Jobs", desc: "Creates product feature jobs" },
  "research-init": { name: "Research Init", desc: "Creates a new research project" },
  "research-phase": { name: "Research Phase", desc: "Internal single-phase primitive for periodic or manual special paths" },
  "research-cycle": { name: "Research Cycle", desc: "Runs a full research pass to a terminal state" },
};

export async function listAgents(): Promise<AgentInfo[]> {
  const out: AgentInfo[] = [];

  // Captain = Operator / agent system (brain, workflows, jobs); not a chat agent.
  out.push({
    id: "captain",
    name: "Captain",
    description: "Operator: brain, workflows, jobs. Runs autonomously, not in Telegram.",
    source: "workflow",
    details: "Not a separate agent, but the system label for the brain starting workflows.",
  });

  // June = OpenClaw generalist; delegates execution to ARGUS.
  try {
    const identityPath = path.join(AGENT_WORKSPACE, "IDENTITY.md");
    const raw = await readFile(identityPath, "utf-8");
    const nameMatch = raw.match(/\*\*Name:\*\*\s*(\S+)/);
    const creatureMatch = raw.match(/\*\*Creature:\*\*\s*([^\n*]+)/);
    const vibeMatch = raw.match(/\*\*Vibe:\*\*\s*([^\n*]+)/);
    out.push({
      id: "june",
      name: nameMatch?.[1] ?? "June",
      description: creatureMatch?.[1]?.trim() ?? "The agent you interact with in Telegram.",
      source: "openclaw",
      details: vibeMatch?.[1]?.trim(),
      location: "Server (OpenClaw gateway + Operator; not local desktop)",
    });
  } catch {
    out.push({
      id: "june",
      name: "June",
      description: "The agent you interact with in Telegram. Delegates execution to ARGUS.",
      source: "openclaw",
      location: "Server (OpenClaw gateway + Operator; not local desktop)",
    });
  }

  // Sub-agents: June -> ARGUS -> ATLAS.
  out.push({
    id: "argus",
    name: "ARGUS",
    description: "Senior research engineer. Executes deterministic runs (status, research, full).",
    source: "subagent",
    details: "June starts missions via june-command-run, then execution proceeds through ARGUS and ATLAS.",
    delegationFrom: "june",
  });
  out.push({
    id: "atlas",
    name: "ATLAS",
    description: "Sandbox validation. Promotion gate (GATE_ATLAS).",
    source: "subagent",
    details: "Invoked by ARGUS. June uses the ATLAS result before promotion decisions.",
    delegationFrom: "argus",
  });

  return out;
}

export interface WorkflowInfo {
  id: string;
  name: string;
  description: string;
}

export async function listWorkflows(): Promise<WorkflowInfo[]> {
  const out: WorkflowInfo[] = [];
  const wfPath = path.join(OPERATOR_ROOT, "workflows");
  try {
    const entries = await readdir(wfPath, { withFileTypes: true });
    for (const e of entries) {
      if (!e.isDirectory() && e.name.endsWith(".sh")) {
        const id = e.name.replace(/\.sh$/, "");
        const label = WORKFLOW_LABELS[id] ?? {
          name: id.split("-").map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join(" "),
          desc: "Operator workflow",
        };
        out.push({ id, name: label.name, description: label.desc });
      }
    }
    out.sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    //
  }
  return out;
}
