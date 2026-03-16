"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Crown, FlaskConical, Hammer } from "lucide-react";

const POLL_INTERVAL_MS = 4000;

type Entry = {
  ts: string;
  from: string;
  to: string;
  plan: string;
  request?: string;
  command?: string;
  overall?: string;
  recommendation?: string;
  atlas_overall?: string;
  atlas_recommendation?: string;
  run_dir?: string;
};

type JobSummary = {
  id: string;
  status: string;
};

type HealthResult = {
  healthy?: boolean;
  load_1m?: number;
  disk_used_pct?: number;
};

type ResearchProjectSummary = {
  id: string;
  status: string;
  phase: string;
  experiment_status?: string;
  active_experiment_id?: string;
};

type LiveSnapshot = {
  ts: string;
  activity: { entries: Entry[] };
  jobs: { jobs: JobSummary[]; hasMore?: boolean };
  health: HealthResult;
  research: { projects: ResearchProjectSummary[] };
};

const AGENTS = [
  { id: "june", name: "June", role: "General", color: "#7fc4ea", Icon: Crown },
  { id: "argus", name: "Argus", role: "Research", color: "#d9a56f", Icon: FlaskConical },
  { id: "atlas", name: "Atlas", role: "Sandbox", color: "#84b998", Icon: Hammer },
] as const;

function entryKey(e: Entry): string {
  return `${e.ts}-${e.from}-${e.to}-${e.plan}`;
}

function displayCommand(e: Entry): string {
  if (e.command) return e.command;
  const req = e.request?.trim() ? ` \"${e.request.slice(0, 80)}${e.request.length > 80 ? "…" : ""}\"` : "";
  if (e.from === "june" && e.to === "argus") return `argus-research-run ${e.plan}${req}`;
  if (e.from === "argus" && e.to === "atlas") return `atlas-sandbox-run ${e.plan}${req}`;
  return `${e.plan}${req}`;
}

function fmtTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

function relTime(ts: string): string {
  try {
    const diffSec = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
    if (diffSec < 20) return "now";
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    return `${Math.floor(diffMin / 60)}h ago`;
  } catch {
    return ts;
  }
}

function short(text: string, n = 100): string {
  return text.length > n ? `${text.slice(0, n)}…` : text;
}

function streamLabel(mode: "connecting" | "live" | "fallback" | "error") {
  if (mode === "live") return "Live";
  if (mode === "fallback") return "Polling";
  if (mode === "error") return "Reconnect";
  return "Connecting";
}

export default function AgentActivityPage() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [health, setHealth] = useState<HealthResult | null>(null);
  const [projects, setProjects] = useState<ResearchProjectSummary[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState<number>(() => Date.now());
  const [streamMode, setStreamMode] = useState<"connecting" | "live" | "fallback" | "error">("connecting");

  useEffect(() => {
    const t = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let stopped = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let es: EventSource | null = null;

    const applySnapshot = (snap: LiveSnapshot) => {
      if (stopped) return;
      setEntries(snap.activity?.entries ?? []);
      setJobs(snap.jobs?.jobs ?? []);
      setHealth(snap.health ?? null);
      setProjects(snap.research?.projects ?? []);
      setError(null);
      setLoading(false);
    };

    const fetchSnapshot = async () => {
      try {
        const r = await fetch("/api/live-stream?snapshot=1", { cache: "no-store" });
        const data = (await r.json()) as LiveSnapshot & { error?: string };
        if (data.error) throw new Error(data.error);
        applySnapshot(data);
      } catch (e) {
        if (!stopped) {
          setError(String((e as Error).message));
          setLoading(false);
        }
      }
    };

    const startPolling = () => {
      if (pollTimer) return;
      setStreamMode("fallback");
      void fetchSnapshot();
      pollTimer = setInterval(() => {
        void fetchSnapshot();
      }, POLL_INTERVAL_MS);
    };

    void fetchSnapshot();

    if (typeof EventSource !== "undefined") {
      es = new EventSource("/api/live-stream");
      es.onopen = () => {
        if (!stopped) setStreamMode("live");
      };
      es.addEventListener("snapshot", (ev) => {
        try {
          const snap = JSON.parse((ev as MessageEvent).data) as LiveSnapshot;
          applySnapshot(snap);
        } catch (e) {
          if (!stopped) setError(`snapshot parse error: ${String((e as Error).message)}`);
        }
      });
      es.onerror = () => {
        if (stopped) return;
        es?.close();
        es = null;
        setStreamMode("error");
        startPolling();
      };
    } else {
      startPolling();
    }

    return () => {
      stopped = true;
      if (es) es.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, []);

  const newest = entries[0] ?? null;

  const latestByAgent = useMemo(() => {
    const map: Record<string, Entry | null> = { june: null, argus: null, atlas: null };
    for (const e of entries) {
      if (!map[e.from]) map[e.from] = e;
      if (!map[e.to]) map[e.to] = e;
      if (map.june && map.argus && map.atlas) break;
    }
    return map;
  }, [entries]);

  const stats = useMemo(() => {
    const recent = entries.slice(0, 40);
    const minute = nowMs - 60_000;
    const active = new Set<string>();
    let perMin = 0;
    let pass = 0;
    let fail = 0;

    for (const e of recent) {
      const t = new Date(e.ts).getTime();
      if (t >= minute) {
        active.add(e.from);
        active.add(e.to);
        perMin += 1;
      }
      if (e.overall === "PASS") pass += 1;
      if (e.overall === "FAIL") fail += 1;
    }

    const passRatio = pass + fail > 0 ? Math.round((pass / (pass + fail)) * 100) : 100;
    return { activeCount: active.size, perMin, passRatio };
  }, [entries, nowMs]);

  const runningJobs = useMemo(() => jobs.filter((j) => j.status === "RUNNING").length, [jobs]);
  const failedJobs = useMemo(() => jobs.filter((j) => j.status === "FAILED").length, [jobs]);
  const activeProjects = useMemo(() => projects.filter((p) => p.status.toLowerCase() !== "done").length, [projects]);
  const activeExperimentLanes = useMemo(() => projects.filter((p) => p.experiment_status === "running").length, [projects]);

  const healthLabel = health?.healthy ? "healthy" : "degraded";
  const latestDelegations = entries.slice(0, 8);

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-semibold tracking-tight" style={{ color: "#dce6f0" }}>
              Agent Activity
            </h1>
            {!loading && (
              <span
                className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium"
                style={{
                  borderColor: streamMode === "live" ? "#6f8ea9" : "#687383",
                  color: streamMode === "live" ? "#b8ccde" : "#a8b2bd",
                  background: "rgba(17, 24, 34, 0.8)",
                }}
              >
                <span className="h-2 w-2 rounded-full bg-current" />
                {streamLabel(streamMode)}
              </span>
            )}
          </div>
          <p className="mt-2 max-w-2xl text-sm" style={{ color: "#9aa9b8" }}>
            Live delegation flow between June, ARGUS, and ATLAS with job, system, and research status.
          </p>
        </div>
        <Link href="/agents" className="text-sm font-medium underline hover:no-underline" style={{ color: "#9cb3c9" }}>
          ← Agents & Workflows
        </Link>
      </div>

      {loading && <p style={{ color: "#98a7b8" }}>Loading...</p>}
      {error && <p className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-2 text-sm text-red-300">{error}</p>}

      {!loading && !error && entries.length === 0 && (
        <div className="rounded-xl border border-dashed py-12 text-center" style={{ borderColor: "#3a4a5f", color: "#8f9bad" }}>
          No delegations yet.
        </div>
      )}

      {!loading && !error && entries.length > 0 && (
        <div className="space-y-5">
          <section className="rounded-xl border p-4" style={{ borderColor: "#324255", background: "#101925" }}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold" style={{ color: "#d8e5f2" }}>Current Delegation Chain</h2>
              <span className="text-xs" style={{ color: "#8998a9" }}>
                {streamMode === "live" ? "SSE live" : "Fallback polling"}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
              {AGENTS.map((a) => {
                const latest = latestByAgent[a.id];
                const Icon = a.Icon;
                return (
                  <article key={a.id} className="rounded-xl border p-4" style={{ borderColor: "#35475c", background: "#0d1621" }}>
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-full" style={{ background: `${a.color}20`, color: a.color }}>
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="text-base font-semibold" style={{ color: "#dde8f4" }}>{a.name}</div>
                        <div className="text-xs" style={{ color: "#9eb0c2" }}>{a.role}</div>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-[11px]">
                      <span style={{ color: "#92a4b7" }}>status</span>
                      <span style={{ color: latest?.overall === "FAIL" ? "#cf8b8b" : latest ? "#93b89a" : "#9eb0c2" }}>
                        {latest?.overall === "FAIL" ? "alert" : latest ? "active" : "idle"}
                      </span>
                    </div>
                    <div className="mt-2 rounded-lg border px-3 py-2 text-[11px] font-mono leading-relaxed" style={{ borderColor: "#324255", background: "#101925", color: "#a6b6c7" }}>
                      {latest ? short(displayCommand(latest), 120) : "No recent command."}
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_1.4fr] gap-5">
            <aside className="space-y-4">
            <section className="grid grid-cols-2 gap-3">
              {[
                { label: "active agents", value: stats.activeCount || 1 },
                { label: "delegations/min", value: stats.perMin },
                { label: "pass ratio", value: `${stats.passRatio}%` },
                { label: "last event", value: newest ? relTime(newest.ts) : "-" },
                { label: "running jobs", value: runningJobs },
                { label: "research active", value: activeProjects },
                { label: "exp lanes", value: activeExperimentLanes },
              ].map((kpi) => (
                <div key={kpi.label} className="rounded-xl border p-3" style={{ borderColor: "#324255", background: "#101925" }}>
                  <div className="text-[11px]" style={{ color: "#92a4b7" }}>{kpi.label}</div>
                  <div className="text-2xl font-semibold" style={{ color: "#dde8f4" }}>{kpi.value}</div>
                </div>
              ))}
            </section>

            <section className="rounded-xl border p-3" style={{ borderColor: "#324255", background: "#101925" }}>
              <h3 className="mb-2 text-sm font-semibold" style={{ color: "#d8e5f2" }}>System Snapshot</h3>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="rounded border px-2 py-1.5" style={{ borderColor: "#35475c", color: "#a0b0c0" }}>
                  health: <strong style={{ color: healthLabel === "healthy" ? "#93b89a" : "#cf8b8b" }}>{healthLabel}</strong>
                </div>
                <div className="rounded border px-2 py-1.5" style={{ borderColor: "#35475c", color: "#a0b0c0" }}>
                  failed jobs: <strong style={{ color: failedJobs > 0 ? "#cf8b8b" : "#dbe6f1" }}>{failedJobs}</strong>
                </div>
                <div className="rounded border px-2 py-1.5" style={{ borderColor: "#35475c", color: "#a0b0c0" }}>
                  load: <strong style={{ color: "#dbe6f1" }}>{health?.load_1m ?? "-"}</strong>
                </div>
                <div className="rounded border px-2 py-1.5" style={{ borderColor: "#35475c", color: "#a0b0c0" }}>
                  disk: <strong style={{ color: "#dbe6f1" }}>{health?.disk_used_pct != null ? `${health.disk_used_pct}%` : "-"}</strong>
                </div>
                <div className="rounded border px-2 py-1.5 col-span-2" style={{ borderColor: "#35475c", color: "#a0b0c0" }}>
                  exp lanes: <strong style={{ color: activeExperimentLanes > 0 ? "#9bd3ff" : "#dbe6f1" }}>{activeExperimentLanes}</strong>
                </div>
              </div>
            </section>
            </aside>

            <section className="rounded-xl border overflow-hidden" style={{ borderColor: "#324255", background: "#101925" }}>
              <div className="px-4 py-2 border-b" style={{ borderColor: "#324255" }}>
                <h2 className="text-sm font-semibold" style={{ color: "#d8e5f2" }}>Inter-Agent Feed</h2>
              </div>
              <div className="max-h-[520px] overflow-y-auto p-3 space-y-2">
                {entries.slice(0, 28).map((e, i) => (
                  <article key={`${entryKey(e)}-${i}`} className="rounded-lg border-l-4 px-3 py-2" style={{ borderLeftColor: AGENTS.find((a) => a.id === e.from)?.color || "#8da0b5", borderColor: "#324255", background: "#0d1621" }}>
                    <div className="flex flex-wrap items-center gap-2 text-[11px]">
                      <span style={{ color: "#8f9faf" }}>[{fmtTime(e.ts)}]</span>
                      <span className="font-semibold capitalize" style={{ color: "#a9c2d9" }}>{e.from}</span>
                      <span style={{ color: "#8393a4" }}>→</span>
                      <span className="font-semibold capitalize" style={{ color: "#dbe6f1" }}>{e.to}</span>
                      <span className="rounded px-1 py-0.5" style={{ background: "#1d2a3a", color: "#9db5cd" }}>{e.plan}</span>
                    </div>
                    <p className="mt-1 text-[11px] font-mono leading-relaxed" style={{ color: "#a6b6c7" }} title={displayCommand(e)}>
                      {short(displayCommand(e), 116)}
                    </p>
                    <div className="mt-1 text-[10px] flex flex-wrap gap-2" style={{ color: "#8fa0b1" }}>
                      {e.overall && <span style={{ color: e.overall === "PASS" ? "#93b89a" : "#cf8b8b" }}>OVERALL={e.overall}</span>}
                      {e.recommendation && <span>REC={e.recommendation}</span>}
                      {e.atlas_overall && <span style={{ color: e.atlas_overall === "PASS" ? "#93b89a" : "#cf8b8b" }}>ATLAS={e.atlas_overall}</span>}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <section className="rounded-xl border overflow-hidden" style={{ borderColor: "#324255", background: "#101925" }}>
            <div className="px-4 py-2 border-b" style={{ borderColor: "#324255" }}>
              <h2 className="text-sm font-semibold" style={{ color: "#d8e5f2" }}>Latest Delegations</h2>
            </div>
            <div className="divide-y" style={{ borderColor: "#324255" }}>
              {latestDelegations.map((e, i) => (
                <div key={`${entryKey(e)}-${i}`} className="grid gap-2 px-4 py-3 lg:grid-cols-[110px_120px_1fr_120px]" style={{ color: "#a6b6c7" }}>
                  <div className="text-[11px] font-mono" style={{ color: "#8f9faf" }}>{fmtTime(e.ts)}</div>
                  <div className="text-[11px]">
                    <span className="capitalize" style={{ color: "#a9c2d9" }}>{e.from}</span>
                    <span style={{ color: "#8393a4" }}> {"->"} </span>
                    <span className="capitalize" style={{ color: "#dbe6f1" }}>{e.to}</span>
                  </div>
                  <div className="text-[11px] font-mono">{displayCommand(e)}</div>
                  <div className="text-[11px]">
                    {e.overall ? (
                      <span style={{ color: e.overall === "PASS" ? "#93b89a" : "#cf8b8b" }}>{e.overall}</span>
                    ) : (
                      <span style={{ color: "#8f9faf" }}>pending</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
