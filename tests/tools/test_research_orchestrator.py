import json

from tools.research_orchestrator import get_experiment_summary


def test_get_experiment_summary_reads_canonical_lane_result(tmp_project):
    exp_id = "exp-20260308010101-abcd1234"
    project = json.loads((tmp_project / "project.json").read_text())
    project["experiment_lane"] = {
        "active_experiment_id": exp_id,
        "artifact_path": f"experiments/{exp_id}",
    }
    (tmp_project / "project.json").write_text(json.dumps(project, indent=2) + "\n")

    exp_dir = tmp_project / "experiments" / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "experiment_result.json").write_text(
        json.dumps(
            {
                "experiment_id": exp_id,
                "lane_status": "candidate_improved",
                "epistemic_status": "unconfirmed",
                "reason_code": "candidate_improvement",
                "best_value": 1.0,
                "terminal_reason": "objective_met_once",
                "gate": {"objective_met": True},
            }
        ),
        encoding="utf-8",
    )

    summary = get_experiment_summary(tmp_project)

    assert "lane_status=candidate_improved" in summary
    assert "epistemic_status=unconfirmed" in summary
    assert "reason_code=candidate_improvement" in summary
    assert "objective_met=True" in summary
