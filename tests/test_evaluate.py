import math

import pandas as pd

from license_pipeline import evaluate


def truth():
    return pd.DataFrame(
        {
            "kind": ["alert"] * 4 + ["dq"],
            "rule": ["r1", "r1", "r1", "r2", "d1"],
            "record_ref": ["a", "b", "c", "x", "k"],
        }
    )


def found(rows):
    return pd.DataFrame(rows, columns=["rule", "record_ref"])


def test_score_counts_true_false_positives_and_misses():
    out = evaluate.score(found([("r1", "a"), ("r1", "b"), ("r1", "z")]), truth(), "alert")
    r1 = out.set_index("rule").loc["r1"]
    assert (r1["tp"], r1["fp"], r1["fn"]) == (2, 1, 1)
    assert math.isclose(r1["precision"], 2 / 3)
    assert math.isclose(r1["recall"], 2 / 3)
    assert r1["false_positives"] == ["z"] and r1["missed"] == ["c"]


def test_score_handles_rule_with_nothing_flagged():
    r2 = evaluate.score(found([("r1", "a")]), truth(), "alert").set_index("rule").loc["r2"]
    assert math.isnan(r2["precision"])
    assert r2["recall"] == 0.0


def test_score_only_covers_requested_kind():
    assert evaluate.score(found([]), truth(), "dq")["rule"].tolist() == ["d1"]


def test_report_lists_rules_counts_and_synthetic_notice():
    alert_scores = evaluate.score(found([("r1", "a")]), truth(), "alert")
    dq_scores = evaluate.score(found([("d1", "k")]), truth(), "dq")
    text = evaluate.render_report(alert_scores, dq_scores, {"contracts": 152})
    assert "synthetic" in text.lower()
    assert "r1" in text and "d1" in text and "152" in text


def test_write_report_creates_file(tmp_path):
    path = evaluate.write_report("hello", tmp_path / "out")
    assert path.read_text() == "hello"
