import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("fs/promises", async (importOriginal) => {
  const actual = await importOriginal<typeof import("fs/promises")>();
  return {
    ...actual,
    readdir: vi.fn(),
    readFile: vi.fn(),
    rm: vi.fn(),
    writeFile: vi.fn(),
    access: vi.fn(),
  };
});
vi.mock("../config", () => ({ OPERATOR_ROOT: "/tmp/operator-root" }));

beforeEach(() => {
  vi.clearAllMocks();
  vi.resetModules();
});

describe("research (data layer)", () => {
  describe("getResearchProject", () => {
    it("throws on invalid project ID (empty)", async () => {
      const { getResearchProject } = await import("../research");
      await expect(getResearchProject("")).rejects.toThrow("Invalid project ID");
    });

    it("throws on invalid project ID (traversal attempt)", async () => {
      const { getResearchProject } = await import("../research");
      await expect(getResearchProject("proj-../../etc/passwd")).rejects.toThrow("Invalid project ID");
    });

    it("throws on ID that does not match proj- pattern", async () => {
      const { getResearchProject } = await import("../research");
      await expect(getResearchProject("other")).rejects.toThrow("Invalid project ID");
    });
  });

  describe("listResearchProjects", () => {
    it("returns empty array when research dir is empty", async () => {
      const { listResearchProjects } = await import("../research");
      const list = await listResearchProjects();
      expect(Array.isArray(list)).toBe(true);
      expect(list).toEqual([]);
    });

    it("returns empty array when research dir does not exist (ENOENT)", async () => {
      const { readdir } = await import("fs/promises");
      const err = new Error("ENOENT") as NodeJS.ErrnoException;
      err.code = "ENOENT";
      vi.mocked(readdir).mockRejectedValueOnce(err);
      const { listResearchProjects } = await import("../research");
      const list = await listResearchProjects();
      expect(list).toEqual([]);
    });
  });

  describe("experiment lane reads", () => {
    it("returns lane summary from canonical experiment result", async () => {
      const { buildExperimentSummary } = await import("../research");
      const summary = buildExperimentSummary(
        {
          active_experiment_id: "exp-20260308010101-abcd1234",
          lane_status: "candidate_improved",
          epistemic_status: "unconfirmed",
          reason_code: "candidate_improvement",
          artifact_path: "experiments/exp-20260308010101-abcd1234",
        },
        {
          experiment_id: "exp-20260308010101-abcd1234",
          run_id: "run-001",
          status: "inconclusive",
          lane_status: "candidate_improved",
          epistemic_status: "unconfirmed",
          reason_code: "candidate_improvement",
          metric_name: "objective_met",
          metric_direction: "max",
          baseline_value: 0,
          best_value: 1,
          runs_attempted: 1,
          terminal_reason: "candidate_only",
        },
      );

      expect(summary?.lane_status).toBe("candidate_improved");
      expect(summary?.epistemic_status).toBe("unconfirmed");
      expect(summary?.reason_code).toBe("candidate_improvement");
      expect(summary?.status).toBe("inconclusive");
    });

    it("falls back to lane semantics when experiment result is malformed or missing", async () => {
      const { buildExperimentSummary } = await import("../research");
      const summary = buildExperimentSummary(
        {
          active_experiment_id: "exp-20260308010101-abcd1234",
          lane_status: "running",
          epistemic_status: "unconfirmed",
          reason_code: "metric_unimproved",
          artifact_path: "experiments/exp-20260308010101-abcd1234",
        },
        null,
      );

      expect(summary?.lane_status).toBe("running");
      expect(summary?.epistemic_status).toBe("unconfirmed");
      expect(summary?.reason_code).toBe("metric_unimproved");
      expect(summary?.status).toBeUndefined();
    });
  });
});
