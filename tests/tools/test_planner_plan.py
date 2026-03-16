"""Tests for planner/system-smoke tightening in tools/planner/plan.py."""

from tools.planner.plan import build_plan, is_system_smoke_question, tighten_plan_for_system_smoke


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text


def test_is_system_smoke_question_detects_control_plane_queries():
    assert is_system_smoke_question("control-plane smoke test validate mission project binding") is True
    assert is_system_smoke_question("latest protein folding papers") is False


def test_tighten_plan_for_system_smoke_trims_breadth():
    plan = {
        "topics": [
            {"id": "t1", "name": "Mission Binding", "priority": 1},
            {"id": "t2", "name": "Runtime Events", "priority": 2},
            {"id": "t3", "name": "Atlas Delegation", "priority": 3},
            {"id": "t4", "name": "Unrelated Breadth", "priority": 3},
        ],
        "queries": [
            {"query": f"query {i}", "topic_id": topic_id, "type": "academic", "perspective": "analyst"}
            for i, topic_id in enumerate(["t1", "t2", "t3", "t4", "t1", "t2", "t3", "t4"], start=1)
        ],
        "perspectives": ["analyst", "skeptic", "operator", "reviewer"],
        "complexity": "complex",
        "estimated_sources_needed": 24,
    }

    out = tighten_plan_for_system_smoke(plan, "control-plane smoke test validate mission project binding")

    assert len(out["topics"]) == 3
    assert len(out["queries"]) <= 8
    assert len(out["queries"]) >= 6
    assert {query["type"] for query in out["queries"]} == {"web"}
    assert out["complexity"] == "simple"
    assert out["estimated_sources_needed"] <= 10
    assert len(out["perspectives"]) <= 3
    assert {query["topic_id"] for query in out["queries"]}.issubset({"t1", "t2", "t3"})


def test_build_plan_applies_system_smoke_tightening(monkeypatch):
    monkeypatch.setattr("tools.planner.plan.research_mode_for_project", lambda project_id: "standard")
    monkeypatch.setattr("tools.planner.plan.load_prior_knowledge_and_questions", lambda project_id: ("", "", []))
    monkeypatch.setattr("tools.planner.plan.planner_memory.load_strategy_context", lambda question, project_id: None)
    monkeypatch.setattr("tools.planner.plan.planner_memory.persist_strategy_context", lambda project_id, ctx: None)
    monkeypatch.setattr("tools.planner.plan.planner_memory.apply_strategy_to_plan", lambda plan, ctx: plan)
    monkeypatch.setattr(
        "tools.planner.plan.llm_call",
        lambda *args, **kwargs: _Resp(
            '{"topics": ['
            '{"id": "t1", "name": "Mission Binding", "priority": 1, "description": "Core control-plane binding", "source_types": ["docs"], "min_sources": 2},'
            '{"id": "t2", "name": "Runtime Events", "priority": 2, "description": "Runtime events and ordering", "source_types": ["docs"], "min_sources": 2},'
            '{"id": "t3", "name": "Atlas Delegation", "priority": 3, "description": "Delegation contract integrity", "source_types": ["docs"], "min_sources": 1}'
            '],'
            '"perspectives": ["analyst", "runtime engineer", "tester", "skeptic"],'
            '"queries": ['
            '{"query": "mission binding contract", "topic_id": "t1", "type": "academic", "perspective": "analyst"},'
            '{"query": "runtime event ordering", "topic_id": "t2", "type": "academic", "perspective": "runtime engineer"},'
            '{"query": "atlas delegation contract", "topic_id": "t3", "type": "academic", "perspective": "tester"}'
            '],'
            '"complexity": "complex",'
            '"estimated_sources_needed": 18}'
        ),
    )

    out = build_plan("control-plane smoke test validate mission project binding", "proj-test")

    assert out["complexity"] == "simple"
    assert out["estimated_sources_needed"] <= 10
    assert len(out["queries"]) <= 8
    assert len(out["queries"]) >= 6
    assert {query["type"] for query in out["queries"]} == {"web"}
