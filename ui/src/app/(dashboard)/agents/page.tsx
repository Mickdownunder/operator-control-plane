import Link from "next/link";
import { listAgents, listWorkflows, type AgentInfo, type WorkflowInfo } from "@/lib/operator/agents";
import { ALLOWED_WORKFLOWS } from "@/lib/operator/actions";

export const dynamic = "force-dynamic";

type WorkflowCategory =
  | "research"
  | "tools"
  | "infra"
  | "brain"
  | "product"
  | "other";

const CATEGORY_META: Record<
  WorkflowCategory,
  { label: string; short: string; order: number }
> = {
  research: { label: "Research", short: "Research runs", order: 0 },
  brain: { label: "Brain & Quality", short: "Planning, review", order: 1 },
  tools: { label: "Tools", short: "Idea, eval, use", order: 2 },
  infra: { label: "Infrastructure", short: "Status, signals", order: 3 },
  product: { label: "Product", short: "Spec, scaffold", order: 4 },
  other: { label: "Other", short: "Knowledge, goals", order: 5 },
};

function getWorkflowCategory(id: string): WorkflowCategory {
  if (id === "research-init" || id === "research-cycle") return "research";
  if (id === "planner" || id === "critic" || id === "prioritize") return "brain";
  if (id.startsWith("tool-")) return "tools";
  if (
    id === "infra-status" ||
    id === "signals" ||
    id === "autopilot-infra" ||
    id === "propose-infra"
  )
    return "infra";
  if (id.startsWith("product-")) return "product";
  return "other";
}

function AgentCard({
  agent,
  showDelegationBox = true,
  compact = false,
}: {
  agent: AgentInfo;
  showDelegationBox?: boolean;
  compact?: boolean;
}) {
  const isCaptain = agent.id === "captain";
  const isJune = agent.id === "june";
  const isSubagent = agent.source === "subagent";
  const badgeLabel =
    agent.source === "openclaw"
      ? "OpenClaw · Telegram"
      : agent.source === "subagent"
        ? "Sub-Agent"
        : "Operator";
  const icon = isCaptain ? "⚙" : isJune ? "💬" : agent.id === "argus" ? "🔬" : agent.id === "atlas" ? "🛡" : "•";
  return (
    <div
      className={`rounded-xl border p-6 transition-colors hover:border-tron-accent/40 ${compact ? "p-4" : ""}`}
      style={{
        borderColor: "var(--tron-border)",
        background:
          isCaptain || isJune
            ? "linear-gradient(135deg, color-mix(in srgb, var(--tron-accent) 6%, transparent) 0%, var(--tron-bg-panel) 100%)"
            : isSubagent
              ? "linear-gradient(135deg, color-mix(in srgb, var(--tron-accent) 4%, transparent) 0%, var(--tron-bg-panel) 100%)"
              : "var(--tron-bg-panel)",
      }}
    >
      <div className="flex items-start gap-4">
        <div
          className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg text-xl"
          style={{
            background: isCaptain
              ? "color-mix(in srgb, var(--tron-accent) 18%, transparent)"
              : isJune
                ? "color-mix(in srgb, var(--tron-success, #22c55e) 18%, transparent)"
                : isSubagent
                  ? "color-mix(in srgb, var(--tron-accent) 12%, transparent)"
                  : "var(--tron-bg)",
            border: "1px solid var(--tron-border)",
          }}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className={`font-semibold ${compact ? "text-base" : "text-lg"}`} style={{ color: "var(--tron-text)" }}>
              {agent.name}
            </h3>
            {agent.delegationFrom && (
              <span className="text-[10px]" style={{ color: "var(--tron-text-dim)" }}>
                {"<-"} delegated from {agent.delegationFrom}
              </span>
            )}
            <span
              className="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider"
              style={{
                background:
                  agent.source === "openclaw"
                    ? "color-mix(in srgb, var(--tron-success, #22c55e) 15%, transparent)"
                    : "color-mix(in srgb, var(--tron-accent) 15%, transparent)",
                color: "var(--tron-text)",
                border: "1px solid var(--tron-border)",
              }}
            >
              {badgeLabel}
            </span>
          </div>
          {agent.description && (
            <p className="mt-1.5 text-sm leading-snug" style={{ color: "var(--tron-text-muted)" }}>
              {agent.description}
            </p>
          )}
          {agent.details && (
            <p className="mt-1 text-xs" style={{ color: "var(--tron-text-dim)" }}>
              {agent.details}
            </p>
          )}
          {agent.location && (
            <p className="mt-1.5 text-[11px]" style={{ color: "var(--tron-text-dim)" }}>
              <span className="font-medium">Runs on:</span> {agent.location}
            </p>
          )}
          {showDelegationBox && (isCaptain || isJune) && (
            <div className="mt-4 rounded-lg border py-2.5 px-3" style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg)" }}>
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>
                {isCaptain ? "Responsibilities" : "Uses / delegates"}
              </div>
              <ul className="mt-1.5 space-y-0.5 text-sm" style={{ color: "var(--tron-text)" }}>
                {isCaptain && (
                  <>
                    <li><strong>Brain</strong> — Perceive → Understand → Think → Decide → Act → Reflect</li>
                    <li><strong>Workflows</strong> - all scripts listed below (`op job new` + `op run`)</li>
                    <li><strong>Plumber</strong> - self-healing for repeated workflow failures</li>
                  </>
                )}
                {isJune && (
                  <>
                    <li><strong>Research</strong> - `/research-start`, `/research-cycle`, `/research-go`, `/research-feedback`</li>
                    <li><strong>Jobs</strong> - starts workflows via `op`</li>
                    <li><strong>Command Plane</strong> - `june-command-run` compiles missions; execution flows through ARGUS {"->"} ATLAS</li>
                  </>
                )}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkflowRow({
  workflow,
  allowedFromUi,
}: {
  workflow: WorkflowInfo;
  allowedFromUi: boolean;
}) {
  return (
    <tr
      className="border-b transition-colors last:border-b-0 hover:bg-tron-accent/5"
      style={{ borderColor: "var(--tron-border)" }}
    >
      <td className="py-3 pr-3">
        <span className="font-medium" style={{ color: "var(--tron-text)" }}>
          {workflow.name}
        </span>
      </td>
      <td className="py-3 pr-3 font-mono text-xs" style={{ color: "var(--tron-text-dim)" }}>
        {workflow.id}
      </td>
      <td className="py-3 pr-3 text-sm" style={{ color: "var(--tron-text-muted)" }}>
        {workflow.description}
      </td>
      <td className="py-3 pl-3 text-right">
        {allowedFromUi && (
          <span
            className="inline-block rounded px-2 py-0.5 text-[10px] font-semibold"
            style={{
              background: "color-mix(in srgb, var(--tron-accent) 20%, transparent)",
              color: "var(--tron-accent)",
              border: "1px solid color-mix(in srgb, var(--tron-accent) 40%, transparent)",
            }}
          >
            Quick-Action
          </span>
        )}
      </td>
    </tr>
  );
}

export default async function AgentsPage() {
  const [agents, workflows] = await Promise.all([listAgents(), listWorkflows()]);

  const byCategory = workflows.reduce<Record<WorkflowCategory, WorkflowInfo[]>>(
    (acc, w) => {
      const cat = getWorkflowCategory(w.id);
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(w);
      return acc;
    },
    {} as Record<WorkflowCategory, WorkflowInfo[]>
  );

  const orderedCategories = (Object.entries(CATEGORY_META) as [WorkflowCategory, typeof CATEGORY_META[WorkflowCategory]][])
    .sort((a, b) => a[1].order - b[1].order)
    .filter(([cat]) => (byCategory[cat]?.length ?? 0) > 0);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Who decides what? The system does. */}
      <div
        className="rounded-xl border p-5"
        style={{
          borderColor: "color-mix(in srgb, var(--tron-accent) 35%, transparent)",
          background: "linear-gradient(135deg, color-mix(in srgb, var(--tron-accent) 8%, transparent) 0%, var(--tron-bg-panel) 100%)",
        }}
      >
        <h2 className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--tron-accent)" }}>
          You do not choose workflows. The system does.
        </h2>
        <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--tron-text)" }}>
          You only provide the <strong>research question</strong> or the <strong>goal</strong>. The <strong>brain</strong> decides which workflow runs and when: it sees open research projects, uses memory and principles, and starts the public <em>research-cycle</em> path, <em>planner</em>, or whatever fits next. You do not click individual workflows. You start research or a brain cycle and the system chooses the next action.
        </p>
        <ul className="mt-3 space-y-1 text-sm" style={{ color: "var(--tron-text-muted)" }}>
          <li><strong className="text-tron-text">Research:</strong> enter a question, the system creates the project and runs all phases to the report.</li>
          <li><strong className="text-tron-text">Everything else:</strong> start a brain cycle, the brain uses state and memory, chooses the next action, and runs the right workflow.</li>
        </ul>
      </div>

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: "var(--tron-text)" }}>
            Agents & Workflows
          </h1>
          <p className="mt-1 max-w-xl text-sm" style={{ color: "var(--tron-text-muted)" }}>
            Captain = Operator (brain/workflows). June = Telegram agent that delegates to ARGUS {"->"} ATLAS. This page shows what the brain can run.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/agents/command"
            className="rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:opacity-90"
            style={{
              borderColor: "var(--tron-border)",
              background: "color-mix(in srgb, var(--tron-success, #22c55e) 12%, transparent)",
              color: "var(--tron-text)",
            }}
          >
            Command Center →
          </Link>
          <Link
            href="/agents/activity"
            className="rounded-lg border px-3 py-2 text-sm font-medium transition-colors hover:opacity-90"
            style={{
              borderColor: "var(--tron-border)",
              background: "color-mix(in srgb, var(--tron-accent) 12%, transparent)",
              color: "var(--tron-accent)",
            }}
          >
            Agent Activity →
          </Link>
        </div>
      </div>

      {/* Primary agents: Captain (Operator), June (OpenClaw) */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>
          Primary Agents
        </h2>
        <div className="grid gap-5 sm:grid-cols-2">
          {agents.filter((a) => a.source !== "subagent").map((a) => (
            <AgentCard key={a.id} agent={a} />
          ))}
        </div>
      </section>

      {/* Delegation chain: June -> ARGUS -> ATLAS */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>
          Delegation Chain (June)
        </h2>
        <p className="mb-4 text-sm" style={{ color: "var(--tron-text-muted)" }}>
          June delegates execution to ARGUS, and ARGUS uses ATLAS for sandbox validation. Before promotion decisions, GATE_ATLAS and other gates must pass.
        </p>
        <div className="flex flex-wrap items-stretch gap-2">
          <span className="flex items-center px-2 text-sm font-medium" style={{ color: "var(--tron-text)" }}>June</span>
          <span className="flex items-center text-sm" style={{ color: "var(--tron-text-dim)" }} aria-hidden>→</span>
          {agents
            .filter((a) => a.source === "subagent")
            .sort((a, b) => (a.id === "argus" ? 0 : 1) - (b.id === "argus" ? 0 : 1))
            .map((a, i) => (
              <span key={a.id} className="contents">
                {i > 0 && <span className="flex items-center text-sm" style={{ color: "var(--tron-text-dim)" }} aria-hidden>→</span>}
                <AgentCard agent={a} showDelegationBox={false} compact />
              </span>
            ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-4 text-xs" style={{ color: "var(--tron-text-dim)" }}>
          <span>June: june-command-run --execute (Mission Control)</span>
          <span>ARGUS {"->"} ATLAS: sandbox runs, GATE_ATLAS</span>
        </div>
      </section>

      {/* ── Bounded Experiment Lane ────────────────────────────── */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>
          Bounded Experiment Lane
        </h2>
        <div
          className="rounded-xl border p-5"
          style={{
            borderColor: "color-mix(in srgb, var(--tron-accent) 28%, transparent)",
            background: "linear-gradient(135deg, color-mix(in srgb, var(--tron-accent) 6%, transparent) 0%, var(--tron-bg-panel) 100%)",
          }}
        >
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider" style={{ background: "color-mix(in srgb, var(--tron-accent) 18%, transparent)", color: "var(--tron-text)", border: "1px solid var(--tron-border)" }}>
              Operator Worker Lane
            </span>
            <span className="text-sm font-semibold" style={{ color: "var(--tron-text)" }}>
              Not a new agent, but a bounded experiment worker under June/Operator
            </span>
          </div>
          <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--tron-text-muted)" }}>
            This lane is the controlled experimentation layer in the style of Karpathy's <span className="font-mono">autoresearch</span>: clear brief, narrow scope, short sandbox runs, machine-readable result. <strong>June remains the global orchestrator</strong>, <strong>Operator remains the epistemic truth layer</strong>, and the worker only writes bounded artifacts and ingestable results.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm">
            <div className="rounded-lg border p-3" style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg)" }}>
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>Flow</div>
              <div className="mt-1" style={{ color: "var(--tron-text)" }}>
                Synthesize → Experiment Worker → Operator Ingest → June Next Decision
              </div>
            </div>
            <div className="rounded-lg border p-3" style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg)" }}>
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>Writes</div>
              <div className="mt-1 font-mono text-[12px]" style={{ color: "var(--tron-text)" }}>
                experiment_brief.json<br />
                experiment_trace.jsonl<br />
                experiment_result.json
              </div>
            </div>
            <div className="rounded-lg border p-3" style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg)" }}>
              <div className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>Guardrails</div>
              <div className="mt-1" style={{ color: "var(--tron-text)" }}>
                no new orchestrator, no new truth layer, idempotent start, bounded sandbox only after synthesize
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Workflows by category */}
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>
          Captain's Workflows by Category
        </h2>
        <p className="mb-4 text-sm" style={{ color: "var(--tron-text-muted)" }}>
          The brain can start all <span className="font-mono text-tron-accent">{workflows.length}</span> workflows. <strong>Quick Action</strong> means it is also available as a button in Command Center, but the brain can choose it automatically.
        </p>

        <div className="space-y-6">
          {orderedCategories.map(([cat]) => {
            const meta = CATEGORY_META[cat];
            const list = byCategory[cat] ?? [];
            return (
              <div
                key={cat}
                className="rounded-xl border overflow-hidden"
                style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg-panel)" }}
              >
                <div
                  className="flex items-center gap-2 px-4 py-2.5"
                  style={{ borderBottom: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}
                >
                  <span className="font-semibold text-sm" style={{ color: "var(--tron-accent)" }}>
                    {meta.label}
                  </span>
                  <span className="text-xs" style={{ color: "var(--tron-text-dim)" }}>
                    {meta.short}
                  </span>
                  <span className="ml-auto font-mono text-[10px]" style={{ color: "var(--tron-text-dim)" }}>
                    {list.length} Workflow{list.length !== 1 ? "s" : ""}
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[520px] text-sm">
                    <thead>
                      <tr className="text-left text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-muted)" }}>
                        <th className="p-3">Name</th>
                        <th className="p-3">ID</th>
                        <th className="p-3">Description</th>
                        <th className="p-3 w-24 text-right">Quick-Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {list.map((w) => (
                        <WorkflowRow
                          key={w.id}
                          workflow={w}
                          allowedFromUi={ALLOWED_WORKFLOWS.has(w.id)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>

        {workflows.length === 0 && (
          <p className="rounded-lg border border-dashed py-8 text-center text-sm" style={{ borderColor: "var(--tron-border)", color: "var(--tron-text-dim)" }}>
            No workflows found (`workflows/*.sh`).
          </p>
        )}
      </section>

      {/* Quick reference */}
      <section
        className="rounded-lg border p-4"
        style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg)" }}
      >
        <h3 className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-dim)" }}>
          Quick Reference
        </h3>
        <ul className="mt-2 space-y-1 text-xs" style={{ color: "var(--tron-text-muted)" }}>
          <li><strong className="text-tron-text">Research:</strong> enter a question on the Research page. The system starts and runs to the report.</li>
          <li><strong className="text-tron-text">Brain:</strong> <Link href="/memory" className="underline hover:text-tron-accent">Memory &amp; Graph</Link> shows brain status, episodes, and principles. A brain cycle chooses the next workflow automatically.</li>
          <li><strong className="text-tron-text">Quick Actions:</strong> optional controls in Command Center. The brain still decides what runs by default.</li>
        </ul>
      </section>
    </div>
  );
}
