"""Build research plan via LLM and optional Memory v2 strategy overlay."""
import json
import sys
from pathlib import Path
from typing import Any

from tools.research_common import llm_call, research_root
from tools.planner.constants import PLANNER_MODEL
from tools.planner.helpers import json_only
from tools.planner.sanitize import sanitize_plan
from tools.planner.fallback import fallback_plan
from tools.planner.prior import load_prior_knowledge_and_questions, research_mode_for_project
from tools.planner import memory as planner_memory


SYSTEM_SMOKE_PHRASES = (
    "control plane",
    "control-plane",
    "smoke test",
    "system smoke",
    "mission project binding",
    "project binding",
    "operator health",
    "runtime event",
    "contract validation",
    "research control event",
)
SYSTEM_SMOKE_KEYWORDS = {
    "june",
    "operator",
    "argus",
    "atlas",
    "mission",
    "project",
    "control",
    "runtime",
    "binding",
    "health",
    "status",
    "validate",
    "validation",
    "contract",
    "smoke",
}
SYSTEM_SMOKE_QUERY_HINTS = (
    "mission project binding",
    "control plane events",
    "operator project status",
    "june mission timeline",
    "argus atlas delegation contract",
    "runtime event sequence",
)


def is_system_smoke_question(question: str) -> bool:
    text = " ".join(str(question or "").lower().split())
    if not text:
        return False
    if any(phrase in text for phrase in SYSTEM_SMOKE_PHRASES):
        return True
    hits = sum(1 for keyword in SYSTEM_SMOKE_KEYWORDS if keyword in text)
    return hits >= 3 and any(marker in text for marker in ("test", "validate", "validation", "check", "health", "binding", "runtime"))


def tighten_plan_for_system_smoke(plan: dict[str, Any], question: str) -> dict[str, Any]:
    topics = [dict(topic) for topic in (plan.get("topics") or []) if isinstance(topic, dict)]
    queries = [dict(query) for query in (plan.get("queries") or []) if isinstance(query, dict)]
    if not topics or not queries:
        return plan

    topics = sorted(topics, key=lambda topic: int(topic.get("priority") or 3))[:3]
    allowed_topic_ids = {topic["id"] for topic in topics if topic.get("id")}
    filtered_queries = []
    seen_queries = set()
    for query in queries:
        topic_id = query.get("topic_id")
        if topic_id not in allowed_topic_ids:
            continue
        normalized_query = " ".join(str(query.get("query") or "").split())
        if not normalized_query:
            continue
        key = normalized_query.lower()
        if key in seen_queries:
            continue
        seen_queries.add(key)
        query["query"] = normalized_query
        query["type"] = "web"
        filtered_queries.append(query)
        if len(filtered_queries) >= 6:
            break

    while len(filtered_queries) < 6 and topics:
        topic = topics[len(filtered_queries) % len(topics)]
        hint = SYSTEM_SMOKE_QUERY_HINTS[len(filtered_queries) % len(SYSTEM_SMOKE_QUERY_HINTS)]
        filtered_queries.append(
            {
                "query": f"{question.strip()} {hint}"[:180],
                "topic_id": topic["id"],
                "type": "web",
                "perspective": "system operator",
            }
        )

    perspectives = [str(p) for p in (plan.get("perspectives") or []) if str(p).strip()]
    if not perspectives:
        perspectives = ["system operator", "runtime engineer", "integration tester"]

    return {
        **plan,
        "topics": topics,
        "queries": filtered_queries[:8],
        "perspectives": perspectives[:3],
        "complexity": "simple",
        "estimated_sources_needed": min(10, max(4, int(plan.get("estimated_sources_needed") or len(filtered_queries)))),
    }


def load_project_plan(project_id: str) -> dict[str, Any]:
    plan_path = research_root() / project_id / "research_plan.json"
    if not plan_path.exists():
        return {"topics": [], "entities": [], "perspectives": []}
    try:
        return json.loads(plan_path.read_text())
    except Exception:
        return {"topics": [], "entities": [], "perspectives": []}


def build_plan(question: str, project_id: str) -> dict[str, Any]:
    research_mode = research_mode_for_project(project_id)
    prior_snippet, questions_snippet, _ = load_prior_knowledge_and_questions(project_id)

    if research_mode == "discovery":
        system = """You are a research strategist for DISCOVERY mode: breadth over depth, novel connections, hypothesis generation.
Goal: Maximize diversity of sources, perspectives, and adjacent fields. We are NOT trying to verify one answer — we are exploring what is unknown, where evidence is missing, and what competing hypotheses exist."""
        user = f"""
QUESTION: {question}{prior_snippet}{questions_snippet}

Create a DISCOVERY research plan (broad, hypothesis-seeking). Return JSON with keys:
1) topics: [{{id,name,priority,description,source_types,min_sources}}] — include adjacent fields and "where evidence is missing"
2) entities: [specific systems, papers, people, approaches]
3) perspectives: [5-8 diverse perspectives, e.g. clinical researcher, skeptic, industry, policy, adjacent domain]
4) queries: [{{query,topic_id,type,perspective}}]
   - 20-40 queries (more than standard)
   - English
   - max 12 words each
   - Include: competing hypotheses, emerging approaches, gaps, "what we don't know", adjacent fields
   - type: "web" | "academic" | "medical" — use "academic"/"medical" for papers and trials where relevant
   - Every entity and topic from multiple angles (supporting, critical, alternative)
5) complexity: prefer "moderate" or "complex" for discovery
6) estimated_sources_needed: integer (e.g. 30-60 for breadth)

Return ONLY JSON."""
    else:
        system = "You are a senior research strategist planning a comprehensive investigation."
        user = f"""
QUESTION: {question}{prior_snippet}{questions_snippet}

Create a research plan. Return JSON with keys:
1) topics: [{{id,name,priority,description,source_types,min_sources}}]
2) entities: [specific systems/papers/people]
3) perspectives: [3-6 perspectives]
4) queries: [{{query,topic_id,type,perspective}}]
   - 15-30 queries
   - English
   - max 10 words each
   - every entity gets at least one dedicated query
   - each topic gets queries from multiple perspectives
   - type: "web" | "academic" | "medical"
   - Use "medical" for health/biomedical/clinical queries (searches PubMed)
   - Use "academic" for scientific/technical papers (Semantic Scholar + ArXiv)
   - Use "web" for general information
5) complexity: simple|moderate|complex
6) estimated_sources_needed: integer

Return ONLY JSON.
""".strip()

    try:
        resp = llm_call(PLANNER_MODEL, system, user, project_id=project_id)
        base = sanitize_plan(json_only(resp.text), question)
        print(f"PLANNER: LLM plan generated ({len(base.get('queries', []))} queries, {len(base.get('topics', []))} topics){' [discovery]' if research_mode == 'discovery' else ''}", file=sys.stderr)
    except Exception as exc:
        print(f"PLANNER: LLM call failed ({type(exc).__name__}: {exc}), using fallback", file=sys.stderr)
        base = fallback_plan(question)
    strategy_ctx = planner_memory.load_strategy_context(question, project_id)
    plan = planner_memory.apply_strategy_to_plan(base, strategy_ctx)
    if research_mode != "discovery" and is_system_smoke_question(question):
        plan = tighten_plan_for_system_smoke(plan, question)
    planner_memory.persist_strategy_context(project_id, strategy_ctx)
    return plan
