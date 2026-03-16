/** Runtime state from progress API (computed server-side). */
export type RuntimeState =
  | "RUNNING"
  | "IDLE"
  | "STUCK"
  | "ERROR_LOOP"
  | "FAILED"
  | "DONE";

export interface ProgressApiResponse {
  state: RuntimeState;
  is_running: boolean;
  data: {
    phase?: string;
    step?: string;
    step_started_at?: string;
    step_index?: number;
    step_total?: number;
    steps_completed?: Array<{ ts: string; step: string; duration_s: number }>;
    active_steps?: Array<{ step: string; started_at: string }>;
    heartbeat?: string;
    started_at?: string;
    last_error?: { code: string; message: string; at: string };
  } | null;
  heartbeat_at: string | null;
  heartbeat_age_s: number | null;
  pid_alive: boolean;
  last_progress_at: string | null;
  last_error: { code: string; message: string; at: string } | null;
  error_counts_5m: Record<string, number>;
  loop_signature: string | null;
  stuck_reason: string | null;
  phase: string | null;
  step: string | null;
  step_started_at: string | null;
  events: Array<{ ts: string; event: string; code?: string; message?: string; step?: string; phase?: string }>;
  project_status: string;
}

export const RUNTIME_STATE_LABELS: Record<RuntimeState, string> = {
  RUNNING: "Running",
  IDLE: "Idle",
  STUCK: "Stuck",
  ERROR_LOOP: "Error loop",
  FAILED: "Failed",
  DONE: "Done",
};

export const RUNTIME_STATE_HINT: Record<RuntimeState, string> = {
  RUNNING: "Process active, current step is executing",
  IDLE: "No running process, waiting for a trigger",
  STUCK: "No progress for 5 minutes, process appears stuck",
  ERROR_LOOP: "Same error is repeating, intervention required",
  FAILED: "Run aborted",
  DONE: "Completed successfully",
};
