"use client";

import { LoadingSpinner } from "@/components/LoadingSpinner";

type ExperimentTraceEntry = {
  ts?: string;
  run_id?: string;
  iteration?: number;
  status?: string;
  decision?: string;
  metric_value?: number;
  baseline_value?: number;
  best_value_before_run?: number;
  best_value_after_run?: number;
  execution_success?: boolean;
  objective_met?: boolean;
  timeout?: boolean;
  artifact_path?: string;
};

type ExperimentData = {
  brief: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  trace: ExperimentTraceEntry[];
};

export function ExperimentTab({
  experiment,
  loading,
}: {
  experiment: ExperimentData | null;
  loading: boolean;
}) {
  if (loading) return <LoadingSpinner />;
  if (!experiment) {
    return (
      <div className="py-10 text-center">
        <p className="text-sm" style={{ color: "var(--tron-text-muted)" }}>No experiment lane data.</p>
        <p className="mt-1 text-xs" style={{ color: "var(--tron-text-dim)" }}>
          No bounded experiment brief, trace, or result artifacts were found for this project.
        </p>
      </div>
    );
  }

  const result = experiment.result ?? {};
  const brief = experiment.brief ?? {};
  const trace = experiment.trace ?? [];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div className="stat-card">
          <div className="metric-label">Lane</div>
          <div className="mt-1 text-lg font-bold font-mono" style={{ color: "var(--tron-text)" }}>
            {typeof result.lane_status === "string" ? result.lane_status : "running"}
          </div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Epistemic</div>
          <div className="mt-1 text-lg font-bold font-mono" style={{ color: "var(--tron-text)" }}>
            {typeof result.epistemic_status === "string" ? result.epistemic_status : "unconfirmed"}
          </div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Reason</div>
          <div className="mt-1 text-[12px] font-bold font-mono" style={{ color: "var(--tron-text)" }}>
            {typeof result.reason_code === "string" ? result.reason_code : "—"}
          </div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Runs</div>
          <div className="mt-1 text-2xl font-bold font-mono" style={{ color: "var(--tron-accent)" }}>
            {typeof result.runs_attempted === "number" ? result.runs_attempted : trace.length}
          </div>
        </div>
        <div className="stat-card">
          <div className="metric-label">Metric</div>
          <div className="mt-1 text-lg font-bold font-mono" style={{ color: "var(--tron-text)" }}>
            {typeof result.metric_name === "string" ? `${result.metric_name}` : "objective_met"}
          </div>
          {typeof result.best_value === "number" && (
            <p className="mt-0.5 text-[10px]" style={{ color: "var(--tron-text-dim)" }}>
              best = {String(result.best_value)}
            </p>
          )}
        </div>
        <div className="stat-card">
          <div className="metric-label">Terminal</div>
          <div className="mt-1 text-[12px] font-mono" style={{ color: "var(--tron-text)" }}>
            {typeof result.terminal_reason === "string" ? result.terminal_reason : "—"}
          </div>
        </div>
      </div>

      <div className="rounded-lg border p-4" style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg-panel)" }}>
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-accent)" }}>
          Experiment Brief
        </div>
        <div className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <div className="metric-label">Hypothesis</div>
            <p style={{ color: "var(--tron-text)" }}>{typeof brief.hypothesis === "string" ? brief.hypothesis : "—"}</p>
          </div>
          <div>
            <div className="metric-label">Objective</div>
            <p style={{ color: "var(--tron-text)" }}>{typeof brief.objective === "string" ? brief.objective : "—"}</p>
          </div>
          <div>
            <div className="metric-label">Command</div>
            <p className="font-mono text-[12px]" style={{ color: "var(--tron-text)" }}>{typeof brief.run_command === "string" ? brief.run_command : "—"}</p>
          </div>
          <div>
            <div className="metric-label">Acceptance</div>
            <p className="font-mono text-[12px]" style={{ color: "var(--tron-text)" }}>{typeof brief.acceptance_rule === "string" ? brief.acceptance_rule : "—"}</p>
          </div>
          <div>
            <div className="metric-label">Revert</div>
            <p className="font-mono text-[12px]" style={{ color: "var(--tron-text)" }}>{typeof brief.revert_rule === "string" ? brief.revert_rule : "—"}</p>
          </div>
          <div>
            <div className="metric-label">Editable Paths</div>
            <p className="font-mono text-[12px]" style={{ color: "var(--tron-text)" }}>
              {Array.isArray(brief.editable_paths) ? brief.editable_paths.join(", ") : "—"}
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-lg border p-4" style={{ borderColor: "var(--tron-border)", background: "var(--tron-bg-panel)" }}>
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-accent)" }}>
          Run Trace
        </div>
        {trace.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--tron-text-muted)" }}>No run trace yet.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Decision</th>
                <th>Metric</th>
                <th>Best</th>
                <th>Exec</th>
                <th>Timeout</th>
              </tr>
            </thead>
            <tbody>
              {trace.map((entry) => (
                <tr key={entry.run_id ?? String(entry.iteration)}>
                  <td className="font-mono text-[11px]">{entry.run_id ?? entry.iteration ?? "—"}</td>
                  <td className="font-mono text-[11px]">{entry.status ?? "—"}</td>
                  <td className="font-mono text-[11px]">{entry.decision ?? "—"}</td>
                  <td className="font-mono text-[11px]">{entry.metric_value != null ? String(entry.metric_value) : "—"}</td>
                  <td className="font-mono text-[11px]">{entry.best_value_after_run != null ? String(entry.best_value_after_run) : "—"}</td>
                  <td className="font-mono text-[11px]">{entry.execution_success ? "yes" : "no"}</td>
                  <td className="font-mono text-[11px]">{entry.timeout ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
