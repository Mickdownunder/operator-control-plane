"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const PLAYBOOKS = [
  { id: "general", label: "General" },
  { id: "market_analysis", label: "Market Analysis" },
  { id: "literature_review", label: "Literature Review" },
  { id: "patent", label: "Patent Landscape" },
  { id: "due_diligence", label: "Due Diligence" },
];

const RESEARCH_MODES = [
  { id: "standard", label: "Standard Research", desc: "Market analysis, competitive intel — cross-source verification required" },
  { id: "frontier", label: "Frontier Research", desc: "Academic, bleeding-edge — single authoritative source can suffice" },
  { id: "discovery", label: "Discovery Research", desc: "Novel ideas, hypothesis generation — Knowledge Graph mining, cross-domain patterns, gap detection" },
];

export function CreateProjectForm() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [playbookId, setPlaybookId] = useState("general");
  const [researchMode, setResearchMode] = useState<"standard" | "frontier" | "discovery">("standard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!question.trim()) {
      setError("Enter a research question.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/research/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim(), playbook_id: playbookId, research_mode: researchMode }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error ?? "Request failed");
        return;
      }
      if (data.ok) {
        router.refresh();
        setQuestion("");
        setError("");
      }
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setLoading(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="tron-panel space-y-5 p-6"
      suppressHydrationWarning
    >
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-tron-text">
          New Research Project
        </h2>
        <p className="mt-1 text-sm text-tron-dim">
          All phases run automatically. No manual "next phase" clicks required. The report appears when the run is complete.
        </p>
      </div>
      <div className="space-y-4">
        <div>
          <label htmlFor="question" className="mb-1.5 block text-sm font-medium text-tron-muted">
            What do you want to research?
          </label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. market size for vertical SaaS in the EU"
            rows={3}
            className="w-full rounded-sm border-2 border-tron-border bg-tron-bg px-4 py-3 text-sm text-tron-text placeholder-tron-dim focus:border-tron-accent focus:outline-none focus:shadow-[0_0_15px_var(--tron-glow)] transition-all"
            disabled={loading}
            suppressHydrationWarning
          />
        </div>
        <div>
          <label htmlFor="playbook" className="mb-1.5 block text-sm font-medium text-tron-muted">
            Playbook
          </label>
          <select
            id="playbook"
            value={playbookId}
            onChange={(e) => setPlaybookId(e.target.value)}
            className="w-full rounded-sm border-2 border-tron-border bg-tron-bg px-4 py-3 text-sm text-tron-text focus:border-tron-accent focus:outline-none focus:shadow-[0_0_15px_var(--tron-glow)] transition-all appearance-none"
            disabled={loading}
            suppressHydrationWarning
          >
            {PLAYBOOKS.map((p) => (
              <option key={p.id} value={p.id} className="bg-tron-bg text-tron-text">
                {p.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="research_mode" className="mb-1.5 block text-sm font-medium text-tron-muted">
            Research mode
          </label>
          <select
            id="research_mode"
            value={researchMode}
            onChange={(e) => setResearchMode(e.target.value as "standard" | "frontier" | "discovery")}
            className="w-full rounded-sm border-2 border-tron-border bg-tron-bg px-4 py-3 text-sm text-tron-text focus:border-tron-accent focus:outline-none focus:shadow-[0_0_15px_var(--tron-glow)] transition-all appearance-none"
            disabled={loading}
            suppressHydrationWarning
          >
            {RESEARCH_MODES.map((m) => (
              <option key={m.id} value={m.id} className="bg-tron-bg text-tron-text">
                {m.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-[11px]" style={{ color: "var(--tron-text-dim)" }}>
            {RESEARCH_MODES.find((m) => m.id === researchMode)?.desc}
          </p>
        </div>
      </div>
      {error && <p className="text-sm font-medium text-tron-error">{error}</p>}
      <div className="pt-2">
        <button
          type="submit"
          disabled={loading}
          className="flex h-11 w-full items-center justify-center rounded-sm bg-transparent border-2 border-tron-accent px-4 font-bold text-tron-accent shadow-[0_0_15px_var(--tron-glow)] transition-all hover:bg-tron-accent hover:text-black hover:shadow-[0_0_25px_var(--tron-glow)] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 sm:w-auto uppercase tracking-widest"
        >
          {loading ? "Initializing, please wait..." : "Start Research"}
        </button>
      </div>
    </form>
  );
}
