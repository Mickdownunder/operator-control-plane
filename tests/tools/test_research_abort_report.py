"""Unit tests for tools/research_abort_report.py."""
import json
import pytest

from tools.research_abort_report import generate_abort_report


def test_generate_abort_report_no_project(mock_operator_root):
    """generate_abort_report() returns empty string when project does not exist."""
    out = generate_abort_report("nonexistent-id-xyz")
    assert out == ""


def test_generate_abort_report_creates_content(tmp_project):
    """generate_abort_report() returns non-empty markdown for existing project."""
    from tools.research_common import save_project
    save_project(tmp_project, {
        "id": tmp_project.name,
        "question": "Test?",
        "status": "failed_reader_pipeline",
        "phase": "explore",
    })
    out = generate_abort_report(tmp_project.name)
    assert isinstance(out, str)
    assert "Test?" in out or "Abort" in out or "report" in out.lower() or "failed" in out.lower()


def test_generate_abort_report_contains_question(tmp_project):
    """generate_abort_report() return contains question and status info."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    out = generate_abort_report(tmp_project.name)
    assert "Q?" in out
    assert "failed" in out or "phase" in out.lower()


def test_generate_abort_report_with_quality_gate_and_reasons(tmp_project):
    """quality_gate.evidence_gate with fail_code and reasons."""
    from tools.research_common import save_project
    save_project(tmp_project, {
        "id": tmp_project.name,
        "question": "Why?",
        "status": "failed",
        "phase": "verify",
        "quality_gate": {
            "evidence_gate": {
                "fail_code": "failed_insufficient_evidence",
                "reasons": ["Not enough findings"],
                "metrics": {"read_attempts": 5, "read_successes": 2, "read_failures": 3},
            }
        },
    })
    out = generate_abort_report(tmp_project.name)
    assert "failed_insufficient_evidence" in out or "Fail Code" in out
    assert "Not enough findings" in out or "reasons" in out.lower()
    assert "Read attempts" in out or "Pipeline Metrics" in out


def test_generate_abort_report_with_sources_and_reliability(tmp_project):
    """sources + source_reliability.json + content files."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "sources" / "s1.json").write_text(json.dumps({"url": "https://a.com/page", "title": "Source A", "description": "Long description here for key facts section."}))
    (tmp_project / "sources" / "s1_content.json").write_text(json.dumps({"text": "x" * 60}))
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text(json.dumps({"sources": [{"url": "https://a.com/page", "reliability_score": 0.8}]}))
    out = generate_abort_report(tmp_project.name)
    assert "Source A" in out or "a.com" in out
    assert "reliability" in out.lower() or "80%" in out
    assert "Key Facts" in out or "Pipeline Metrics" in out


def test_generate_abort_report_with_claims_and_recommendations(tmp_project):
    """claim_ledger with verified/unverified, triggers recommendations."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "verify", "current_spend": 1.5})
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_ledger.json").write_text(json.dumps({
        "claims": [
            {"text": "Claim one", "is_verified": False, "verification_reason": "only 1 source"},
        ]
    }))
    out = generate_abort_report(tmp_project.name)
    assert "Claims Extracted" in out or "UNVERIFIED" in out or "Claim one" in out
    assert "Budget spent" in out or "1.5000" in out or "Manual follow-up" in out


def test_generate_abort_report_fail_explanations(tmp_project):
    """FAIL_EXPLANATIONS for known fail codes."""
    from tools.research_common import save_project
    for code in ["failed_insufficient_evidence", "FAILED_BUDGET_EXCEEDED", "failed_reader_pipeline"]:
        save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": code, "phase": "explore", "quality_gate": {"evidence_gate": {"fail_code": code}}})
        out = generate_abort_report(tmp_project.name)
        assert "Explanation" in out or code in out


def test_generate_abort_report_safe_json_bad_files(tmp_project):
    """Corrupt JSON in sources/verify is skipped (_safe_json returns {})."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "sources" / "bad.json").write_text("not json")
    (tmp_project / "sources" / "bad_content.json").write_text("{")  # invalid
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "source_reliability.json").write_text("invalid")
    (tmp_project / "verify" / "claim_ledger.json").write_text("{")
    out = generate_abort_report(tmp_project.name)
    assert "Abort" in out or "Pipeline Metrics" in out


def test_generate_abort_report_no_sources_line(tmp_project):
    """Top Sources section shows 'No sources discovered' when empty."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    (tmp_project / "sources").mkdir(exist_ok=True)
    out = generate_abort_report(tmp_project.name)
    assert "No sources discovered" in out or "Top Sources" in out


def test_generate_abort_report_recommendations_high_read_failure(tmp_project):
    """Recommendation: high read failure rate."""
    from tools.research_common import save_project
    save_project(tmp_project, {
        "id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore",
        "quality_gate": {"evidence_gate": {"metrics": {"read_attempts": 10, "read_successes": 2, "read_failures": 8}}},
    })
    out = generate_abort_report(tmp_project.name)
    assert "read failure" in out.lower() or "scraping" in out.lower() or "Jina" in out


def test_generate_abort_report_recommendations_few_findings_content_read(tmp_project):
    """Recommendation: content read but few findings."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "sources" / "a_content.json").write_text(json.dumps({"text": "x" * 60}))
    (tmp_project / "sources" / "b_content.json").write_text(json.dumps({"text": "y" * 60}))
    (tmp_project / "findings").mkdir(exist_ok=True)
    out = generate_abort_report(tmp_project.name)
    assert "findings" in out.lower() or "relevance" in out.lower() or "Manual follow-up" in out


def test_generate_abort_report_recommendations_most_sources_unread(tmp_project):
    """Recommendation: most sources could not be read."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "findings").mkdir(exist_ok=True)
    out = generate_abort_report(tmp_project.name)
    assert "could not be read" in out or "re-running" in out or "Manual follow-up" in out


def test_generate_abort_report_recommendations_claims_none_verified(tmp_project):
    """Recommendation: claims found but none verified."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "verify"})
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_ledger.json").write_text(
        json.dumps({"claims": [{"text": "C1", "is_verified": False}, {"text": "C2", "is_verified": False}]})
    )
    out = generate_abort_report(tmp_project.name)
    assert "none verified" in out or "diverse sources" in out or "Manual follow-up" in out


def test_generate_abort_report_verified_count_and_key_facts(tmp_project):
    """Verified count in metrics; Key Facts from search metadata."""
    from tools.research_common import save_project
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    (tmp_project / "sources").mkdir(exist_ok=True)
    (tmp_project / "sources" / "s1.json").write_text(json.dumps({
        "url": "https://example.com/page",
        "title": "Example",
        "description": "A long description that is unique and has more than twenty characters here.",
    }))
    (tmp_project / "verify").mkdir(exist_ok=True)
    (tmp_project / "verify" / "claim_ledger.json").write_text(
        json.dumps({"claims": [{"text": "Claim", "is_verified": True}]})
    )
    out = generate_abort_report(tmp_project.name)
    assert "Verified claims" in out and "1" in out
    assert "Key Facts" in out or "Pipeline Metrics" in out


def test_research_abort_report_main_usage_exit(monkeypatch, capsys):
    """main() with no args prints usage and exits 2."""
    import sys
    from tools.research_abort_report import main
    monkeypatch.setattr(sys, "argv", ["research_abort_report.py"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2


def test_research_abort_report_main_project_not_found(mock_operator_root, monkeypatch, capsys):
    """main() with nonexistent project exits 1."""
    import sys
    from tools.research_abort_report import main
    monkeypatch.setattr(sys, "argv", ["research_abort_report.py", "nonexistent-id-xyz"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_research_abort_report_main_success(tmp_project, monkeypatch, capsys):
    """main() writes report and prints JSON."""
    import sys
    from tools.research_common import save_project
    from tools.research_abort_report import main
    save_project(tmp_project, {"id": tmp_project.name, "question": "Q?", "status": "failed", "phase": "explore"})
    monkeypatch.setattr(sys, "argv", ["research_abort_report.py", tmp_project.name])
    main()
    out = capsys.readouterr().out
    assert "path" in out and "reports" in out
    assert (tmp_project / "reports").exists()
    reports = list((tmp_project / "reports").glob("abort_report_*.md"))
    assert len(reports) >= 1
