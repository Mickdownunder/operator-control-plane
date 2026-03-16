"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Discovery-only form: one question, research_mode fixed to "discovery".
 * No playbook/research-mode select. For open-ended, hypothesis-driven research
 * (e.g. "How could we cure cancer?", novel connections, emerging concepts).
 */
export function DiscoveryProjectForm() {
  const router = useRouter();
  const [question, setQuestion] = useState("");
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
        body: JSON.stringify({
          question: question.trim(),
          playbook_id: "general",
          research_mode: "discovery",
        }),
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
        if (data.projectId) {
          router.push(`/research/${data.projectId}`);
        }
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
          Novel / Discovery Research
        </h2>
        <p className="mt-1 text-sm text-tron-dim">
          Breadth before depth: new ideas, hypotheses, gaps, and cross-domain connections. Evidence gates and phases are tuned for discovery work, including lighter verification and novelty-focused review.
        </p>
      </div>
      <div className="space-y-4">
        <div>
          <label htmlFor="discovery-question" className="mb-1.5 block text-sm font-medium text-tron-muted">
            What do you want to explore? (open-ended, ambitious)
          </label>
          <textarea
            id="discovery-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. How could we cure cancer? What new approaches exist? Where are the largest gaps?"
            rows={3}
            className="w-full rounded-sm border-2 border-tron-border bg-tron-bg px-4 py-3 text-sm text-tron-text placeholder-tron-dim focus:border-tron-accent focus:outline-none focus:shadow-[0_0_15px_var(--tron-glow)] transition-all"
            disabled={loading}
            suppressHydrationWarning
          />
        </div>
      </div>
      {error && <p className="text-sm font-medium text-tron-error">{error}</p>}
      <div className="pt-2">
        <button
          type="submit"
          disabled={loading}
          className="flex h-11 w-full items-center justify-center rounded-sm bg-transparent border-2 border-tron-accent px-4 font-bold text-tron-accent shadow-[0_0_15px_var(--tron-glow)] transition-all hover:bg-tron-accent hover:text-black hover:shadow-[0_0_25px_var(--tron-glow)] active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 sm:w-auto uppercase tracking-widest"
        >
          {loading ? "Initializing, please wait..." : "Start Discovery"}
        </button>
      </div>
    </form>
  );
}
