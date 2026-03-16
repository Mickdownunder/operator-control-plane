"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import type {
  CampaignSummary,
  CommandCenterData,
  CommandMissionSummary,
  CommandMissionTask,
  PortfolioSummary,
} from "@/lib/operator/command-center";

type ActionName = "create" | "show" | "pause" | "resume" | "retry" | "replan" | "reset_mission" | "reset_campaign" | "reset_portfolio_signals" | "archive_mission" | "unarchive_mission" | "bulk_archive_done";

type CommandCenterClientProps = {
  initialData: CommandCenterData;
  initialSelectedMissionId?: string;
};

const QUICK_TEMPLATES = [
  {
    label: "Status",
    objective: "Primary control-plane status validation",
    requestText: "status check",
  },
  {
    label: "Mini",
    objective: "Primary control-plane mini validation",
    requestText: "mini_fast",
  },
  {
    label: "Research",
    objective: "Primary control-plane research validation",
    requestText: "research cycle validation on current operator stack",
  },
];

export function CommandCenterClient({ initialData, initialSelectedMissionId }: CommandCenterClientProps) {
  const [data, setData] = useState(initialData);
  const [selectedMissionId, setSelectedMissionId] = useState(initialSelectedMissionId ?? initialData.missions[0]?.id ?? "");
  const [objective, setObjective] = useState(QUICK_TEMPLATES[0].objective);
  const [requestText, setRequestText] = useState(QUICK_TEMPLATES[0].requestText);
  const [executeImmediately, setExecuteImmediately] = useState(true);
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<ActionName | null>(null);
  const [planFilter, setPlanFilter] = useState<"all" | "status" | "mini" | "research">("all");
  const [archivePage, setArchivePage] = useState(1);

  const openMissions = useMemo(() => data.missions.filter((mission) => !mission.archived), [data.missions]);
  const archivedMissions = useMemo(() => data.missions.filter((mission) => mission.archived), [data.missions]);

  const selectedMission = useMemo(
    () => data.missions.find((mission) => mission.id === selectedMissionId) ?? openMissions[0] ?? archivedMissions[0],
    [data.missions, openMissions, archivedMissions, selectedMissionId],
  );

  const filteredOpenMissions = useMemo(() => planFilter === "all" ? openMissions : openMissions.filter((mission) => mission.plan === planFilter), [openMissions, planFilter]);
  const pagedArchivedMissions = useMemo(() => archivedMissions.slice((archivePage - 1) * 10, archivePage * 10), [archivedMissions, archivePage]);
  const archivePages = Math.max(1, Math.ceil(archivedMissions.length / 10));

  const focusMission = useMemo(() => pickFocusMission(filteredOpenMissions), [filteredOpenMissions]);
  const blockedMissions = useMemo(() => data.missions.filter((mission) => mission.lifecycle === "blocked"), [data.missions]);
  const pushCampaigns = useMemo(() => data.campaigns.filter((campaign) => campaign.strategy?.recommended_disposition === "push"), [data.campaigns]);
  const holdCampaigns = useMemo(() => data.campaigns.filter((campaign) => campaign.strategy?.recommended_disposition === "hold"), [data.campaigns]);
  const stopCampaigns = useMemo(() => data.campaigns.filter((campaign) => campaign.strategy?.recommended_disposition === "stop"), [data.campaigns]);
  const topPriorityCampaigns = useMemo(() => {
    const topIds = data.portfolios.flatMap((portfolio) => portfolio.strategy?.top_priority_campaigns ?? []);
    return topIds
      .map((campaignId) => data.campaigns.find((campaign) => campaign.id === campaignId))
      .filter((campaign): campaign is CampaignSummary => Boolean(campaign));
  }, [data.portfolios, data.campaigns]);
  const decisionMissions = useMemo(
    () => data.missions.filter((mission) => mission.lifecycle === "awaiting_next_test" || mission.lifecycle === "blocked"),
    [data.missions],
  );
  const recentCompleted = useMemo(
    () => data.missions.find((mission) => mission.lifecycle === "done"),
    [data.missions],
  );

  useEffect(() => {
    if (!selectedMissionId && (openMissions[0]?.id || archivedMissions[0]?.id)) {
      setSelectedMissionId(openMissions[0]?.id ?? archivedMissions[0]?.id ?? "");
    }
  }, [archivedMissions, openMissions, selectedMissionId]);

  useEffect(() => {
    const active = data.missions.some(
      (mission) => mission.lifecycle === "active" || mission.lifecycle === "awaiting_next_test" || mission.status === "planned",
    );
    if (!active) return;
    const interval = window.setInterval(() => {
      void refreshData(setData, setError);
    }, 10000);
    return () => window.clearInterval(interval);
  }, [data.missions]);

  async function runAction(action: ActionName, overrides: Record<string, unknown> = {}) {
    setBusy(action);
    setError(null);
    setMessage(null);
    try {
      const response = await fetch("/api/command-center", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          missionId: selectedMission?.id,
          objective,
          requestText,
          reason,
          execute: executeImmediately,
          ...overrides,
        }),
      });
      const result = await response.json();
      if (!response.ok || !result.ok) {
        throw new Error(result.error ?? "Command action failed");
      }
      if (result.data) {
        setData(result.data as CommandCenterData);
      }
      if (result.mission?.id) {
        setSelectedMissionId(result.mission.id);
      }
      if (action === "archive_mission" && selectedMission?.id === result.mission?.id) {
        setSelectedMissionId((result.data as CommandCenterData | undefined)?.missions.find((mission) => !mission.archived)?.id ?? result.mission.id);
      }
      setMessage(actionMessage(action, result.mission?.id));
      if (action !== "replan") {
        setReason("");
      }
    } catch (actionError) {
      setError(String((actionError as Error).message));
    } finally {
      setBusy(null);
    }
  }

  function applyTemplate(label: string) {
    const template = QUICK_TEMPLATES.find((entry) => entry.label === label);
    if (!template) return;
    setObjective(template.objective);
    setRequestText(template.requestText);
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <section
        className="rounded-[28px] p-6 md:p-8"
        style={{
          border: "1px solid var(--tron-border-strong)",
          background:
            "linear-gradient(135deg, color-mix(in srgb, var(--tron-accent) 8%, transparent) 0%, color-mix(in srgb, var(--tron-bg-panel) 94%, transparent) 58%, var(--tron-bg-panel) 100%)",
          boxShadow: "0 18px 48px color-mix(in srgb, var(--tron-glow-accent) 55%, transparent)",
        }}
      >
        <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr] xl:items-start">
          <div className="space-y-4">
            <div
              className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em]"
              style={{
                background: "color-mix(in srgb, var(--tron-accent) 12%, transparent)",
                color: "var(--tron-accent)",
                border: "1px solid color-mix(in srgb, var(--tron-accent) 28%, transparent)",
              }}
            >
              Master View
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight" style={{ color: "var(--tron-text)" }}>
                June Control Center
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6" style={{ color: "var(--tron-text-muted)" }}>
                This view explains in plain language what June is working on, where decisions are still open, and what should happen next.
                Raw technical data remains available below, but only as optional detail.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              <SummaryCard
                label={focusMission && focusMission.lifecycle === "active" ? "June is currently working on" : "Next open mission"}
                value={focusMission ? focusMission.objective : "No active mission"}
                hint={focusMission ? describeMissionState(focusMission) : "System is currently idle"}
              />
              <SummaryCard
                label="Needs your decision"
                value={decisionMissions[0] ? decisionMissions[0].objective : "Nothing pending"}
                hint={decisionMissions[0] ? describeNextStep(decisionMissions[0]) : "No pending approval or follow-up decision"}
              />
              <SummaryCard
                label="Last clean completion"
                value={recentCompleted ? recentCompleted.objective : "No completed run yet"}
                hint={recentCompleted ? (recentCompleted.envelope?.overall ?? recentCompleted.status) : "Appears once a mission reaches final done"}
              />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <StatTile label="Total missions" value={String(data.stats.totalMissions)} />
            <StatTile label="Active or open" value={String(data.stats.activeMissions)} />
            <StatTile label="Need intervention" value={String(blockedMissions.length)} />
            <StatTile label="Portfolios" value={String(data.stats.portfolios)} />
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <section className="space-y-6">
          <section className="rounded-[24px] p-5 md:p-6" style={panelStyle}>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
                  Start New Mission
                </div>
                <p className="mt-2 text-sm" style={{ color: "var(--tron-text-muted)" }}>
                  Use presets for short standard checks or write a custom mission for June.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {QUICK_TEMPLATES.map((template) => (
                  <button
                    key={template.label}
                    type="button"
                    onClick={() => applyTemplate(template.label)}
                    className="rounded-full px-3 py-1.5 text-xs font-semibold"
                    style={secondaryButtonStyle}
                  >
                    {template.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-5 grid gap-4">
              <label className="grid gap-2 text-sm">
                <span style={{ color: "var(--tron-text-muted)" }}>What should June work on?</span>
                <input
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  className="rounded-2xl px-4 py-3 outline-none"
                  style={fieldStyle}
                  placeholder="Primary control-plane research validation"
                  suppressHydrationWarning
                />
              </label>
              <label className="grid gap-2 text-sm">
                <span style={{ color: "var(--tron-text-muted)" }}>Concrete request / parameters</span>
                <textarea
                  value={requestText}
                  onChange={(event) => setRequestText(event.target.value)}
                  className="min-h-[108px] rounded-2xl px-4 py-3 outline-none"
                  style={fieldStyle}
                  placeholder="mini_fast or a clear research request"
                  suppressHydrationWarning
                />
              </label>
              <label className="inline-flex items-center gap-3 text-sm" style={{ color: "var(--tron-text)" }}>
                <input
                  type="checkbox"
                  checked={executeImmediately}
                  onChange={(event) => setExecuteImmediately(event.target.checked)}
                  suppressHydrationWarning
                />
                Execute immediately after creation
              </label>
              <div className="flex flex-wrap items-center gap-3">
                <ActionButton
                  label={busy === "create" ? "Starting..." : "Start mission"}
                  busy={busy === "create"}
                  tone="primary"
                  onClick={() => runAction("create", { missionId: undefined })}
                />
                <button
                  type="button"
                  onClick={() => void refreshData(setData, setError)}
                  className="rounded-full px-4 py-2 text-sm font-medium"
                  style={secondaryButtonStyle}
                >
                  Refresh
                </button>
              </div>
            </div>
          </section>

          <section className="rounded-[24px] p-5 md:p-6" style={panelStyle}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
                  Strategic Priorities
                </div>
                <p className="mt-2 text-sm" style={{ color: "var(--tron-text-muted)" }}>
                  This section shows which campaigns June should push, hold, or stop right now.
                </p>
              </div>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <SummaryCard
                label="Push"
                value={pushCampaigns[0]?.objective ?? "No priority"}
                hint={pushCampaigns[0] ? describeDisposition(pushCampaigns[0]) : "No line currently has an active push signal"}
              />
              <SummaryCard
                label="Hold"
                value={holdCampaigns[0]?.objective ?? "Nothing on hold"}
                hint={holdCampaigns[0] ? describeDisposition(holdCampaigns[0]) : "No line is waiting for more evidence"}
              />
              <SummaryCard
                label="Stop"
                value={stopCampaigns[0]?.objective ?? "No stop signal"}
                hint={stopCampaigns[0] ? describeDisposition(stopCampaigns[0]) : "No line currently has a stop recommendation"}
              />
            </div>
            {topPriorityCampaigns.length > 0 ? (
              <div className="mt-4 rounded-[20px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>
                  Top Priority Campaigns
                </div>
                <div className="mt-3 space-y-2">
                  {topPriorityCampaigns.slice(0, 3).map((campaign) => (
                    <div key={campaign.id} className="flex items-start justify-between gap-3 text-sm">
                      <div>
                        <div style={{ color: "var(--tron-text)" }}>{campaign.objective}</div>
                        <div style={{ color: "var(--tron-text-muted)" }}>{describeDisposition(campaign)}</div>
                      </div>
                      <ToneBadge value={humanDisposition(campaign.strategy?.recommended_disposition)} kind="mission" />
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </section>

          <section className="rounded-[24px] p-5 md:p-6" style={panelStyle}>
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
                  Missions in Plain Language
                </div>
                <p className="mt-2 text-sm" style={{ color: "var(--tron-text-muted)" }}>
                  Open missions appear first. Archived missions are separated below.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {(["all", "status", "mini", "research"] as const).map((filter) => (
                  <button
                    key={filter}
                    type="button"
                    onClick={() => setPlanFilter(filter)}
                    className="rounded-full px-3 py-1.5 text-xs font-semibold"
                    style={planFilter === filter ? primaryButtonStyle : secondaryButtonStyle}
                  >
                    {filter === "all" ? "All" : filter}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => runAction("bulk_archive_done", { reason: "Bulk archive completed missions" })}
                  className="rounded-full px-3 py-1.5 text-xs font-semibold"
                  style={secondaryButtonStyle}
                >
                  Archive done
                </button>
              </div>
              {selectedMission && <ToneBadge value={humanOverall(selectedMission)} kind="status" />}
            </div>

            <div className="mt-4 grid gap-3">
              {filteredOpenMissions.map((mission) => {
                const active = mission.id === selectedMission?.id;
                return (
                  <button
                    key={mission.id}
                    type="button"
                    onClick={() => setSelectedMissionId(mission.id)}
                    className="grid gap-3 rounded-[22px] p-4 text-left transition-colors"
                    style={{
                      border: active ? "1px solid var(--tron-accent)" : "1px solid var(--tron-border)",
                      background: active ? "color-mix(in srgb, var(--tron-accent) 8%, var(--tron-bg-panel))" : "var(--tron-bg)",
                    }}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="text-base font-semibold" style={{ color: "var(--tron-text)" }}>
                          {mission.objective}
                        </div>
                        <div className="mt-1 text-sm" style={{ color: "var(--tron-text-muted)" }}>
                          {describeMissionState(mission)}
                        </div>
                      </div>
                      <div className="shrink-0">
                        <ToneBadge value={humanOverall(mission)} kind="status" />
                      </div>
                    </div>
                    <div className="grid gap-2 text-sm md:grid-cols-3">
                      <PlainFact label="Next" value={describeNextStep(mission)} />
                      <PlainFact label="Type" value={friendlyPlan(mission.plan)} />
                      <PlainFact label="ID" value={mission.id} mono />
                    </div>
                  </button>
                );
              })}
            </div>
            {archivedMissions.length > 0 ? (
              <details className="mt-4 rounded-[20px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
                <summary className="cursor-pointer list-none text-sm font-semibold" style={{ color: "var(--tron-text)" }}>
                  Archived Missions ({archivedMissions.length})
                </summary>
                <div className="mt-3 grid gap-3">
                  {pagedArchivedMissions.map((mission) => (
                    <button
                      key={mission.id}
                      type="button"
                      onClick={() => setSelectedMissionId(mission.id)}
                      className="grid gap-2 rounded-[18px] p-3 text-left transition-colors"
                      style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg-panel)" }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold" style={{ color: "var(--tron-text)" }}>{mission.objective}</div>
                          <div className="mt-1 text-xs" style={{ color: "var(--tron-text-muted)" }}>
                            Archived {mission.archived_at ?? ""}
                          </div>
                        </div>
                        <ToneBadge value="ARCHIVED" kind="mission" />
                      </div>
                    </button>
                  ))}
                </div>
                {archivePages > 1 ? (
                  <div className="mt-3 flex items-center justify-between gap-3 text-sm">
                    <button type="button" onClick={() => setArchivePage((page) => Math.max(1, page - 1))} className="rounded-full px-3 py-1.5" style={secondaryButtonStyle}>Back</button>
                    <span style={{ color: "var(--tron-text-muted)" }}>Page {archivePage} / {archivePages}</span>
                    <button type="button" onClick={() => setArchivePage((page) => Math.min(archivePages, page + 1))} className="rounded-full px-3 py-1.5" style={secondaryButtonStyle}>Next</button>
                  </div>
                ) : null}
              </details>
            ) : null}
          </section>
        </section>

        <aside className="space-y-6">
          <section className="rounded-[24px] p-5 md:p-6" style={panelStyle}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
                  Selected Mission
                </div>
                {selectedMission ? (
                  <>
                    <h2 className="mt-2 text-xl font-semibold" style={{ color: "var(--tron-text)" }}>
                      {selectedMission.objective}
                    </h2>
                    <p className="mt-2 text-sm leading-6" style={{ color: "var(--tron-text-muted)" }}>
                      {describeMissionForHuman(selectedMission)}
                    </p>
                  </>
                ) : (
                  <p className="mt-2 text-sm" style={{ color: "var(--tron-text-muted)" }}>No mission selected.</p>
                )}
              </div>
              {selectedMission && <ToneBadge value={humanLifecycle(selectedMission.lifecycle)} kind="mission" />}
            </div>

            {selectedMission && (
              <>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <DetailTile label="June says" value={describeMissionState(selectedMission)} />
                  <DetailTile label="Next step" value={describeNextStep(selectedMission)} />
                  <DetailTile label="Question status" value={describeQuestionStatus(selectedMission)} />
                  <DetailTile label="Evidence progress" value={describeEvidenceDelta(selectedMission)} />
                  <DetailTile label="Countercheck" value={describeCountercheckStatus(selectedMission)} />
                  <DetailTile label="Next best test" value={selectedMission.decision?.next_best_test ?? "No concrete recommendation yet"} />
                  <DetailTile label="Last run" value={selectedMission.envelope?.overall ?? "No result yet"} />
                  <DetailTile label="Atlas" value={selectedMission.envelope?.atlas_overall ?? "n/a"} />
                </div>

                {selectedMission.decision?.why_not_done ? (
                  <div
                    className="mt-4 rounded-[20px] p-4 text-sm leading-6"
                    style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}
                  >
                    <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>
                      Why this is not done yet
                    </div>
                    <div className="mt-2" style={{ color: "var(--tron-text)" }}>{selectedMission.decision.why_not_done}</div>
                  </div>
                ) : null}

                {selectedMission.planning ? (
                  <div className="mt-4 rounded-[20px] p-4 text-sm leading-6" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>
                      Why June is following this line
                    </div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <DetailTile label="Disposition" value={humanPlanningValue(selectedMission.planning.disposition, "No history")} />
                      <DetailTile label="Compute policy" value={humanPlanningValue(selectedMission.planning.computePolicy, "Standard")} />
                      <DetailTile label="Historical risk" value={humanPlanningValue(selectedMission.planning.historicalRisk, "n/a")} />
                      <DetailTile label="Dominant failure pattern" value={humanPlanningValue(selectedMission.planning.dominantFailureGenome, "None")} />
                    </div>
                    {selectedMission.planning.whyThisPlan ? (
                      <div className="mt-3" style={{ color: "var(--tron-text)" }}>
                        <strong>Why this plan:</strong> {selectedMission.planning.whyThisPlan}
                      </div>
                    ) : null}
                    {selectedMission.planning.whyNotPreviousPlan ? (
                      <div className="mt-2" style={{ color: "var(--tron-text)" }}>
                        <strong>Why not the previous plan:</strong> {selectedMission.planning.whyNotPreviousPlan}
                      </div>
                    ) : null}
                    {selectedMission.planning.policyNote ? (
                      <div className="mt-2" style={{ color: "var(--tron-text-muted)" }}>
                        {selectedMission.planning.policyNote}
                      </div>
                    ) : null}
                    {selectedMission.planning.memoryHighlights.length > 0 ? (
                      <div className="mt-3">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>
                          Learned signals from system memory
                        </div>
                        <ul className="mt-2 space-y-1" style={{ color: "var(--tron-text)" }}>
                          {selectedMission.planning.memoryHighlights.map((item) => (
                            <li key={item}>• {item}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                <div className="mt-5 grid gap-2">
                  <label className="grid gap-2 text-sm">
                    <span style={{ color: "var(--tron-text-muted)" }}>Note / reason for the action</span>
                    <input
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      className="rounded-2xl px-4 py-3 outline-none"
                      style={fieldStyle}
                      placeholder="e.g. pause, replan, or retry"
                      suppressHydrationWarning
                    />
                  </label>
                  <div className="flex flex-wrap gap-2">
                    <ActionButton label="Refresh" busy={busy === "show"} onClick={() => runAction("show")} />
                    <ActionButton label="Pause" busy={busy === "pause"} onClick={() => runAction("pause")} />
                    <ActionButton label="Resume" busy={busy === "resume"} onClick={() => runAction("resume", { execute: true })} />
                    <ActionButton label="Retry" busy={busy === "retry"} onClick={() => runAction("retry", { execute: true })} />
                  </div>
                </div>

                <div className="mt-5 grid gap-2">
                  <label className="grid gap-2 text-sm">
                    <span style={{ color: "var(--tron-text-muted)" }}>Replan using this request</span>
                    <textarea
                      value={requestText}
                      onChange={(event) => setRequestText(event.target.value)}
                      className="min-h-[96px] rounded-2xl px-4 py-3 outline-none"
                      style={fieldStyle}
                      suppressHydrationWarning
                    />
                  </label>
                  <ActionButton label="Replan" busy={busy === "replan"} tone="primary" onClick={() => runAction("replan", { execute: true })} />
                </div>

                <div className="mt-5 grid gap-2">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>Reset</div>
                  <div className="flex flex-wrap gap-2">
                    <ActionButton label="Reset mission" busy={busy === "reset_mission"} onClick={() => runAction("reset_mission")} />
                    <ActionButton label="Reset campaign" busy={busy === "reset_campaign"} onClick={() => runAction("reset_campaign")} />
                    <ActionButton label="Reset portfolio signals" busy={busy === "reset_portfolio_signals"} onClick={() => runAction("reset_portfolio_signals")} />
                    {selectedMission?.archived ? (
                      <ActionButton label="Restore" busy={busy === "unarchive_mission"} onClick={() => runAction("unarchive_mission")} />
                    ) : (
                      <ActionButton label="Archive" busy={busy === "archive_mission"} onClick={() => runAction("archive_mission")} />
                    )}
                  </div>
                </div>

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-[20px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
                  <div>
                    <div className="text-sm font-semibold" style={{ color: "var(--tron-text)" }}>Deep details</div>
                    <div className="mt-1 text-xs" style={{ color: "var(--tron-text-muted)" }}>
                      For debugging, artifacts, and the technical state of this mission.
                    </div>
                  </div>
                  <Link href={`/agents/command/${selectedMission.id}`} className="font-medium" style={{ color: "var(--tron-accent)" }}>
                    Open mission detail {"->"}
                  </Link>
                </div>
              </>
            )}
          </section>

          <section className="rounded-[24px] p-5 md:p-6" style={panelStyle}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
              Portfolios and Campaigns
            </div>
            <p className="mt-2 text-sm" style={{ color: "var(--tron-text-muted)" }}>
              This is the mission grouping view. It is for orientation, not day-to-day intervention.
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <CompactPortfolioPanel portfolios={data.portfolios} />
              <CompactCampaignPanel campaigns={data.campaigns} />
            </div>
          </section>

          <details className="rounded-[24px] p-5 md:p-6" style={panelStyle}>
            <summary className="cursor-pointer list-none text-sm font-semibold" style={{ color: "var(--tron-text)" }}>
              Show technical details
            </summary>
            <div className="mt-5 space-y-6">
              <section>
                <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
                  Execution Graph
                </div>
                <div className="mt-4 space-y-3">
                  {selectedMission?.tasks.map((task) => <TaskRow key={task.task_id} task={task} />)}
                </div>
              </section>

              <section>
                <div className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: "var(--tron-text-dim)" }}>
                  Decision / Envelope
                </div>
                <div className="mt-4 grid gap-3">
                  <DetailTile label="Overall" value={selectedMission?.decision?.overall ?? selectedMission?.envelope?.overall ?? "n/a"} />
                  <DetailTile label="Recommendation" value={selectedMission?.envelope?.recommendation ?? "n/a"} />
                  <DetailTile label="Run Dir" value={selectedMission?.envelope?.run_dir ?? "n/a"} mono />
                  <DetailTile label="Summary File" value={selectedMission?.envelope?.summary_file ?? "n/a"} mono />
                  <DetailTile label="Campaign" value={selectedMission?.campaign_id ?? "n/a"} />
                  <DetailTile label="Portfolio" value={selectedMission?.portfolio_id ?? "n/a"} />
                </div>
              </section>
            </div>
          </details>

          {(message || error) && (
            <section
              className="rounded-[24px] p-4"
              style={{
                border: `1px solid ${error ? "color-mix(in srgb, var(--tron-error) 45%, transparent)" : "color-mix(in srgb, var(--tron-success) 35%, transparent)"}`,
                background: error
                  ? "color-mix(in srgb, var(--tron-error) 9%, var(--tron-bg-panel))"
                  : "color-mix(in srgb, var(--tron-success) 8%, var(--tron-bg-panel))",
                color: error ? "var(--tron-error)" : "var(--tron-success)",
              }}
            >
              {error ?? message}
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-[22px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>{label}</div>
      <div className="mt-3 text-base font-semibold leading-6" style={{ color: "var(--tron-text)" }}>{value}</div>
      <div className="mt-2 text-xs leading-5" style={{ color: "var(--tron-text-muted)" }}>{hint}</div>
    </div>
  );
}

function CompactPortfolioPanel({ portfolios }: { portfolios: PortfolioSummary[] }) {
  return (
    <div className="space-y-3">
      {portfolios.slice(0, 4).map((portfolio) => (
        <div key={portfolio.id} className="rounded-[20px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
          <div className="text-sm font-semibold" style={{ color: "var(--tron-text)" }}>{friendlyPortfolio(portfolio.id)}</div>
          <div className="mt-1 text-xs" style={{ color: "var(--tron-text-muted)" }}>{portfolio.campaigns} Campaigns</div>
          <div className="mt-2 text-xs" style={{ color: "var(--tron-text-muted)" }}>
            push {portfolio.strategy?.active_count ?? 0} · hold {portfolio.strategy?.hold_count ?? 0} · stop {portfolio.strategy?.stop_count ?? 0}
          </div>
        </div>
      ))}
    </div>
  );
}

function CompactCampaignPanel({ campaigns }: { campaigns: CampaignSummary[] }) {
  return (
    <div className="space-y-3">
      {campaigns.slice(0, 4).map((campaign) => (
        <div key={campaign.id} className="rounded-[20px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="text-sm font-semibold" style={{ color: "var(--tron-text)" }}>{campaign.objective}</div>
              <div className="mt-1 text-xs" style={{ color: "var(--tron-text-muted)" }}>{friendlyPlan(campaign.plan)} · {campaign.latest?.next_action ?? "n/a"}</div>
              <div className="mt-1 text-xs" style={{ color: "var(--tron-text-muted)" }}>{describeDisposition(campaign)}</div>
            </div>
            <ToneBadge value={humanDisposition(campaign.strategy?.recommended_disposition)} kind="mission" />
          </div>
        </div>
      ))}
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[22px] px-4 py-4" style={{ border: "1px solid var(--tron-border)", background: "color-mix(in srgb, var(--tron-bg-panel) 72%, var(--tron-bg))" }}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>{label}</div>
      <div className="mt-3 text-2xl font-semibold" style={{ color: "var(--tron-text)" }}>{value}</div>
    </div>
  );
}

function PlainFact({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--tron-text-dim)" }}>{label}</div>
      <div className={`mt-1 text-sm ${mono ? "font-mono" : ""}`} style={{ color: "var(--tron-text)" }}>{value}</div>
    </div>
  );
}

function DetailTile({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-[20px] p-4" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.22em]" style={{ color: "var(--tron-text-dim)" }}>{label}</div>
      <div className={`mt-2 break-all text-sm ${mono ? "font-mono" : ""}`} style={{ color: "var(--tron-text)" }}>{value}</div>
    </div>
  );
}

function TaskRow({ task }: { task: CommandMissionTask }) {
  return (
    <div className="rounded-[18px] p-3" style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg)" }}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold" style={{ color: "var(--tron-text)" }}>{task.task_id}</div>
          <div className="mt-1 text-xs leading-5" style={{ color: "var(--tron-text-muted)" }}>{task.description}</div>
        </div>
        <ToneBadge value={task.status} kind="mission" />
      </div>
      {task.depends_on.length > 0 && (
        <div className="mt-2 text-[11px]" style={{ color: "var(--tron-text-dim)" }}>
          depends on: {task.depends_on.join(", ")}
        </div>
      )}
    </div>
  );
}

function ToneBadge({ value, kind }: { value: string; kind: "status" | "mission" }) {
  const normalized = value.toUpperCase();
  const color =
    normalized === "PASS" || normalized === "DONE"
      ? "var(--tron-success)"
      : normalized === "FAIL" || normalized === "FAILED" || normalized === "BLOCKED"
        ? "var(--tron-error)"
        : normalized === "RUNNING" || normalized === "PLANNED" || normalized === "ACTIVE" || normalized === "ARBEITET"
          ? "var(--tron-accent)"
          : "var(--tron-text-muted)";

  return (
    <span
      className="inline-flex min-w-[72px] items-center justify-center rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]"
      style={{
        color,
        background: `color-mix(in srgb, ${color} 12%, transparent)`,
        border: `1px solid color-mix(in srgb, ${color} 28%, transparent)`,
      }}
    >
      {kind === "mission" ? value : normalized}
    </span>
  );
}

function pickFocusMission(missions: CommandMissionSummary[]) {
  return (
    missions.find((mission) => mission.lifecycle === "active") ??
    missions.find((mission) => mission.lifecycle === "awaiting_next_test") ??
    missions.find((mission) => mission.status === "planned") ??
    missions[0]
  );
}

function describeMissionState(mission: CommandMissionSummary) {
  switch (mission.lifecycle) {
    case "active":
      return `June is currently running a ${friendlyPlan(mission.plan)} mission.`;
    case "awaiting_next_test":
      return "The last run succeeded. June recommends the next test.";
    case "done":
      return "This mission is complete.";
    case "blocked":
      return "This mission needs intervention or replanning.";
    case "paused":
      return "This mission is intentionally paused.";
    case "planned":
      return mission.decision?.next_action === "retry"
        ? "This mission is ready for another run but is not executing right now."
        : "This mission is prepared and waiting for execution.";
    default:
      return "The state of this mission is not clearly classified yet.";
  }
}

function describeNextStep(mission: CommandMissionSummary) {
  const next = mission.decision?.next_action ?? "n/a";
  switch (next) {
    case "new_test":
      return "June recommends another test";
    case "stop":
      return "No follow-up action needed";
    case "retry":
      return "Retry";
    case "execute":
      return "Ready to execute";
    case "resume":
      return "Can be resumed";
    default:
      return next;
  }
}

function describeMissionForHuman(mission: CommandMissionSummary) {
  const run = mission.envelope?.overall ? `Last result: ${mission.envelope.overall}.` : "No run result is available yet.";
  return `${describeMissionState(mission)} ${run} ${describeNextStep(mission)}.`;
}

function describeQuestionStatus(mission: CommandMissionSummary) {
  switch (mission.decision?.question_status) {
    case "answered":
      return "The core question is currently answered.";
    case "partially_answered":
      return "The question is partially answered, but not strong enough yet.";
    case "weakly_supported":
      return "The main thesis has some support, but no hard confirmation yet.";
    case "not_answered":
      return "The core question is not answered yet.";
    default:
      return "No reliable question status yet.";
  }
}

function describeEvidenceDelta(mission: CommandMissionSummary) {
  switch (mission.decision?.evidence_delta) {
    case "strong":
      return "Strong new evidence";
    case "moderate":
      return "Solid new evidence";
    case "partial":
      return "Partial new evidence";
    case "weak":
      return "Only weak evidence so far";
    case "negative":
      return "Negative evidence / failed path";
    case "none":
      return "No new evidence yet";
    default:
      return "No assessment yet";
  }
}

function describeCountercheckStatus(mission: CommandMissionSummary) {
  switch (mission.decision?.countercheck_status) {
    case "complete":
      return "Countercheck available";
    case "present_but_unfair":
      return "Countercheck exists, but comparison is still unfair";
    case "missing":
      return "Countercheck still missing";
    case "failed_scope":
      return "Countercheck or scope blocker present";
    default:
      return "No countercheck status yet";
  }
}

function humanOverall(mission: CommandMissionSummary) {
  if (mission.envelope?.overall === "PASS" && mission.lifecycle === "awaiting_next_test") {
    return "OPEN";
  }
  return mission.envelope?.overall ?? humanLifecycle(mission.lifecycle);
}

function humanPlanningValue(value: string | undefined, fallback: string): string {
  if (!value) return fallback;
  return value.replace(/_/g, " ");
}

function humanLifecycle(value: CommandMissionSummary["lifecycle"]) {
  switch (value) {
    case "awaiting_next_test":
      return "open";
    case "active":
      return "active";
    case "done":
      return "done";
    case "paused":
      return "paused";
    case "blocked":
      return "blocked";
    case "planned":
      return "ready";
    default:
      return "unknown";
  }
}

function friendlyPlan(plan: string) {
  switch (plan) {
    case "status":
      return "Status check";
    case "mini":
      return "Mini test";
    case "research":
      return "Research run";
    case "full":
      return "Full run";
    default:
      return plan;
  }
}

function describeDisposition(campaign: CampaignSummary) {
  const disposition = campaign.strategy?.recommended_disposition ?? "hold";
  const avgScore = campaign.strategy?.avg_score;
  const genome = campaign.strategy?.latest_failure_genome;
  const avgText = typeof avgScore === "number" ? `score ${avgScore.toFixed(2)}` : "no score yet";
  switch (disposition) {
    case "push":
      return `June should actively continue this line (${avgText}).`;
    case "stop":
      return `June should stop this line or resume it only with new proof (${genome ?? "no signal"}).`;
    default:
      return `This line should stay on hold until more evidence exists (${genome ?? avgText}).`;
  }
}

function humanDisposition(disposition?: string) {
  switch (disposition) {
    case "push":
      return "push";
    case "stop":
      return "stop";
    default:
      return "hold";
  }
}

function friendlyPortfolio(portfolioId: string) {
  return portfolioId.replace(/^portfolio_/, "").replace(/_/g, " ");
}

function ActionButton({
  label,
  busy,
  onClick,
  tone = "secondary",
}: {
  label: string;
  busy: boolean;
  onClick: () => void;
  tone?: "primary" | "secondary";
}) {
  return (
    <button
      type="button"
      disabled={busy}
      onClick={onClick}
      className="rounded-full px-4 py-2 text-sm font-semibold disabled:opacity-50"
      style={tone === "primary" ? primaryButtonStyle : secondaryButtonStyle}
    >
      {label}
    </button>
  );
}

async function refreshData(
  setData: (data: CommandCenterData) => void,
  setError: (message: string | null) => void,
) {
  try {
    const response = await fetch("/api/command-center", { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error ?? "Refresh failed");
    }
    setData(payload as CommandCenterData);
    setError(null);
  } catch (error) {
    setError(String((error as Error).message));
  }
}

function actionMessage(action: ActionName, missionId?: string) {
  switch (action) {
    case "create":
      return `Mission ${missionId ?? ""} created.`.trim();
    case "pause":
      return "Mission paused.";
    case "resume":
      return "Mission resumed and executed.";
    case "retry":
      return "Mission retried.";
    case "replan":
      return "Mission replanned and restarted.";
    case "show":
      return "Mission refreshed.";
    case "archive_mission":
      return "Mission archived.";
    case "unarchive_mission":
      return "Mission restored.";
    case "bulk_archive_done":
      return "Completed missions archived.";
    case "reset_mission":
      return "Mission reset cleanly.";
    case "reset_campaign":
      return "Campaign state reset.";
    case "reset_portfolio_signals":
      return "Portfolio signals reset.";
    default:
      return "Action completed.";
  }
}

const panelStyle = {
  border: "1px solid var(--tron-border)",
  background: "var(--tron-bg-panel)",
} satisfies CSSProperties;

const fieldStyle = {
  border: "1px solid var(--tron-border)",
  background: "var(--tron-bg)",
  color: "var(--tron-text)",
} satisfies CSSProperties;

const primaryButtonStyle = {
  border: "1px solid color-mix(in srgb, var(--tron-accent) 30%, transparent)",
  background: "color-mix(in srgb, var(--tron-accent) 14%, transparent)",
  color: "var(--tron-text)",
} satisfies CSSProperties;

const secondaryButtonStyle = {
  border: "1px solid var(--tron-border)",
  background: "var(--tron-bg)",
  color: "var(--tron-text)",
} satisfies CSSProperties;
