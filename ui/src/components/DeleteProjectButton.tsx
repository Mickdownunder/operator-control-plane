"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export function DeleteProjectButton({ projectId, projectQuestion }: { projectId: string; projectQuestion?: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  async function handleDelete() {
    const shortQuestion = (projectQuestion || projectId).slice(0, 50);
    if (!confirm(`Delete this research project?\n\n"${shortQuestion}..."\n\nAll findings, sources, and reports will be removed permanently.`)) {
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`/api/research/projects/${encodeURIComponent(projectId)}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { error?: string }).error || `Delete failed (${res.status})`);
      }
      router.push("/research");
      router.refresh();
    } catch (e) {
      alert(String((e as Error).message));
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleDelete}
      disabled={loading}
      className="rounded px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
      style={{
        border: "1px solid var(--tron-error)",
        color: "var(--tron-error)",
        background: "transparent",
      }}
    >
      {loading ? "Deleting..." : "Delete project"}
    </button>
  );
}
