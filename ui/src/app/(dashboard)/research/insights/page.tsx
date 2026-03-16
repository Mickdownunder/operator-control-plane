"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { EmptyState } from "@/components/EmptyState";

interface CrossLinkInsight {
  id: string;
  finding_a_id?: string;
  finding_b_id?: string;
  project_a?: string;
  project_b?: string;
  similarity?: number;
  ts?: string;
}

export default function CrossDomainInsightsPage() {
  const [insights, setInsights] = useState<CrossLinkInsight[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/research/insights")
      .then((r) => r.json())
      .then((d) => setInsights(d.insights ?? []))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/research" className="text-sm text-tron-muted hover:text-tron-accent transition-colors">
          <- Back to overview
        </Link>
      </div>

      <h1 className="text-3xl font-bold tracking-tight text-tron-text">
        Linked Insights
      </h1>

      <p className="max-w-xl text-sm text-tron-muted">
        The system automatically detects semantic connections between results from different research projects.
      </p>

      {loading ? (
        <div className="tron-panel flex justify-center p-8">
          <LoadingSpinner />
        </div>
      ) : insights && insights.length > 0 ? (
        <div className="space-y-4">
          {insights.map((link) => (
            <div
              key={link.id}
              className="tron-panel grid gap-4 p-4 sm:grid-cols-2"
            >
              <div className="rounded border border-tron-border bg-tron-bg p-3">
                <div className="text-xs text-tron-dim">Project A</div>
                <Link
                  href={`/research/${link.project_a ?? ""}`}
                  className="font-medium text-tron-accent hover:underline"
                >
                  {link.project_a ?? link.finding_a_id ?? "—"}
                </Link>
                {link.finding_a_id && (
                  <div className="mt-1 text-xs text-tron-muted">
                    Finding: {link.finding_a_id}
                  </div>
                )}
              </div>
              <div className="rounded border border-tron-border bg-tron-bg p-3">
                <div className="text-xs text-tron-dim">Project B</div>
                <Link
                  href={`/research/${link.project_b ?? ""}`}
                  className="font-medium text-tron-accent hover:underline"
                >
                  {link.project_b ?? link.finding_b_id ?? "—"}
                </Link>
                {link.finding_b_id && (
                  <div className="mt-1 text-xs text-tron-muted">
                    Finding: {link.finding_b_id}
                  </div>
                )}
              </div>
              <div className="sm:col-span-2 flex items-center gap-4">
                {link.similarity != null && (
                  <div className="flex-1">
                    <div className="mb-1 flex justify-between text-xs text-tron-dim">
                      <span>Similarity</span>
                      <span>{Math.round((link.similarity ?? 0) * 100)}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-tron-bg">
                      <div
                        className="h-full rounded-full bg-tron-accent transition-all"
                        style={{
                          width: `${Math.min(100, (link.similarity ?? 0) * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                )}
                {link.ts && (
                  <span className="text-xs text-tron-dim">{link.ts}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState
          title="No cross-domain insights yet."
          description="Connections appear here once multiple research projects contain findings."
        />
      )}
    </div>
  );
}
