import { mkdirSync, rmSync, writeFileSync } from "fs";
import path from "path";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

vi.mock("fs/promises", async (importOriginal) => {
  const actual = await importOriginal<typeof import("fs/promises")>();
  return {
    ...actual,
    readdir: vi.fn(),
    readFile: vi.fn(),
  };
});

const MISSIONS_ROOT = "/root/agent/workspace/logs/missions";

function createMissionFixture(missionId: string, fields: { archivedAt?: string | null } = {}) {
  const missionDir = path.join(MISSIONS_ROOT, missionId);
  mkdirSync(missionDir, { recursive: true });
  writeFileSync(
    path.join(missionDir, "mission.json"),
    JSON.stringify(
      {
        mission_id: missionId,
        objective: "Objective",
        intent: "continue_until_done",
        plan: "research",
        priority: 0.9,
        owner: "june",
        created_at: "2026-03-08T00:00:00Z",
        request_text: "Question",
        status: "running",
        resource_profile: {
          budget_class: "high",
          time_horizon: "multi-hour",
          autonomy_mode: "guided",
          runtime_budget_sec: 7200,
        },
        metadata: {
          portfolio_id: "port-1",
          campaign_id: "camp-1",
          archived_at: fields.archivedAt ?? null,
          portfolio_policy: {
            existing_disposition: "push",
            compute_policy: "frontier",
            note: "Prefer bounded validated runs.",
          },
          strategy_context: {
            historical_risk: "medium",
            why_this_plan: "Matches the current genome.",
            why_not_previous_plan: "Previous run was inconclusive.",
            dominant_failure_genome: "fg-1",
          },
          operator_memory: {
            known_failure_patterns: ["bounded retries"],
            relevant_principles: [{ description: "Prefer validated loops." }],
          },
        },
      },
      null,
      2,
    ) + "\n",
  );
  writeFileSync(
    path.join(missionDir, "task_graph.json"),
    JSON.stringify(
      {
        mission_id: missionId,
        created_at: "2026-03-08T00:00:00Z",
        nodes: [
          {
            task_id: "compile_mission",
            kind: "control",
            description: "compile",
            status: "completed",
            metadata: {},
          },
        ],
      },
      null,
      2,
    ) + "\n",
  );
  writeFileSync(
    path.join(missionDir, "decision.json"),
    JSON.stringify(
      {
        mission_id: missionId,
        overall: "PASS",
        next_action: "new_test",
        mission_status: "running",
        decided_at: "2026-03-08T00:00:02Z",
      },
      null,
      2,
    ) + "\n",
  );
  writeFileSync(
    path.join(missionDir, "result_envelope.json"),
    JSON.stringify(
      {
        overall: "PASS",
        recommendation: "new_test",
        atlas_overall: "PASS",
      },
      null,
      2,
    ) + "\n",
  );
  writeFileSync(
    path.join(missionDir, "operator_binding.json"),
    JSON.stringify(
      {
        mission_id: missionId,
        project_id: "proj-123",
      },
      null,
      2,
    ) + "\n",
  );
  writeFileSync(
    path.join(missionDir, "events.jsonl"),
    JSON.stringify({
      ts: "2026-03-08T00:00:01Z",
      event_type: "mission_execution_started",
      mission_id: missionId,
    }) + "\n",
  );
  return missionDir;
}

describe("command-center", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
  });

  afterEach(() => {
    rmSync(path.join(MISSIONS_ROOT, "mis-1"), { recursive: true, force: true });
    rmSync(path.join(MISSIONS_ROOT, "mis-show"), { recursive: true, force: true });
  });

  it("reads mission details from june canonical summary output", async () => {
    createMissionFixture("mis-1");

    const { readdir, readFile } = await import("fs/promises");
    vi.mocked(readdir)
      .mockResolvedValueOnce([{ name: "mis-1", isDirectory: () => true }] as never)
      .mockResolvedValueOnce(["port-1.json"] as never)
      .mockResolvedValueOnce(["camp-1.json"] as never);
    vi.mocked(readFile).mockImplementation(async (file) => {
      const target = String(file);
      if (target.endsWith("port-1.json")) {
        return JSON.stringify({
          portfolio: { id: "port-1", class: "frontier", owner: "june" },
          campaigns: { "camp-1": {} },
          strategy_summary: { top_priority_campaigns: ["camp-1"] },
        });
      }
      if (target.endsWith("camp-1.json")) {
        return JSON.stringify({
          campaign: { id: "camp-1", plan: "research", objective: "Objective" },
          latest: { overall: "PASS", next_action: "new_test" },
          strategy: { recommended_disposition: "push" },
        });
      }
      throw new Error(`unexpected readFile ${target}`);
    });

    const { listCommandCenter } = await import("../command-center");
    const data = await listCommandCenter();

    const mission = data.missions.find((entry) => entry.id === "mis-1");
    expect(mission).toBeDefined();
    expect(mission).toMatchObject({
      id: "mis-1",
      archived: false,
      portfolio_id: "port-1",
      campaign_id: "camp-1",
      runtime_budget_sec: 7200,
      lifecycle: "awaiting_next_test",
    });
    expect(mission?.planning?.memoryHighlights).toEqual([
      "bounded retries",
      "Prefer validated loops.",
    ]);
    expect(mission?.timeline[0]?.name).toBe("decision_snapshot");
  });

  it("uses june canonical summary for show actions", async () => {
    createMissionFixture("mis-show");

    const { readdir, readFile } = await import("fs/promises");
    vi.mocked(readdir)
      .mockResolvedValueOnce([] as never)
      .mockResolvedValueOnce([] as never)
      .mockResolvedValueOnce([] as never);
    vi.mocked(readFile).mockResolvedValue("{}" as never);

    const { executeCommandCenterAction } = await import("../command-center");
    const result = await executeCommandCenterAction({ action: "show", missionId: "mis-show" });

    expect(result.ok).toBe(true);
    expect(result.command).toEqual([
      expect.stringContaining("/root/agent/workspace/bin/june-command-run"),
      "--mission-id",
      "mis-show",
      "--show",
      "--json",
    ]);
    expect(result.mission?.id).toBe("mis-show");
    expect(result.mission?.timeline.some((entry) => entry.name === "decision_snapshot")).toBe(true);
  });
});
