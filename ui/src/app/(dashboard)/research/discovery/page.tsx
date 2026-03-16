import Link from "next/link";
import { DiscoveryProjectForm } from "@/components/DiscoveryProjectForm";

export const dynamic = "force-dynamic";

export default function DiscoveryResearchPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm mb-1">
            <Link
              href="/research"
              className="font-medium transition-colors hover:underline"
              style={{ color: "var(--tron-text-muted)" }}
            >
              ← Research
            </Link>
          </div>
          <h1 className="text-xl font-semibold tracking-tight" style={{ color: "var(--tron-text)" }}>
            Discovery Research
          </h1>
          <p className="mt-1 text-sm" style={{ color: "var(--tron-text-muted)" }}>
            Dedicated menu and dedicated flow: breadth before depth, hypotheses, gaps, and novel connections. All phases (Explore, Focus, Connect, Verify, Synthesize) behave differently in discovery mode.
          </p>
        </div>
      </div>

      <div
        className="rounded-lg"
        style={{ border: "1px solid var(--tron-border)", background: "var(--tron-bg-panel)" }}
      >
        <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--tron-border)" }}>
          <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--tron-text-muted)" }}>
            New Discovery Project
          </span>
        </div>
        <div className="px-4 py-4">
          <DiscoveryProjectForm />
        </div>
      </div>

      <div className="text-[12px]" style={{ color: "var(--tron-text-dim)" }}>
        <p className="font-medium mb-1">Differences from standard/frontier mode:</p>
        <ul className="list-disc list-inside space-y-0.5 ml-1">
          <li>Evidence gate: no `verified_claim` check; breadth across findings and sources is enough to pass.</li>
          <li>Conductor: `search_more` before `read_more`, delayed verify, synthesize at 8+ domains and 20+ findings.</li>
          <li>After verify: discovery analysis adds `novel_connections`, `emerging_concepts`, `research_frontier`, and `key_hypothesis`.</li>
          <li>Report and critic: novelty is weighted 3x, so 0.5 with high novelty can beat 0.7 without new insight.</li>
        </ul>
      </div>
    </div>
  );
}
