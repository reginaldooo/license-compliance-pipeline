from datetime import UTC, date, datetime

import pandas as pd
import pytest

from license_pipeline import digest

TODAY = date(2026, 11, 18)


def alert(rule, ref, severity, message="msg", contract_id=None):
    return {
        "rule": rule, "record_ref": ref, "contract_id": contract_id,
        "severity": severity, "message": message,
    }


@pytest.fixture
def owners():
    return pd.DataFrame({"owner_id": ["O1", "O2"], "site_id": ["S1", "S2"]})


@pytest.fixture
def contracts():
    return pd.DataFrame({"contract_id": ["C1", "C2"], "owner_id": ["O1", "O2"]})


@pytest.fixture
def alerts():
    return pd.DataFrame(
        [
            alert("renewal_90", "C1", "low", "paris renewal", "C1"),
            alert("renewal_30", "C2", "high", "jakarta renewal", "C2"),
            alert("installs_over_entitlement", "P001|S1", "high", "paris installs"),
            alert("usage_spike", "P002|S2", "medium", "jakarta spike"),
            alert("seat_unused_90d", "SEAT-1", "low", "idle"),
            alert("seat_unused_90d", "AI-1", "low", "idle"),
        ]
    )


def test_alerts_for_site_keeps_only_that_sites_alerts(alerts, contracts, owners):
    out = digest.alerts_for_site(alerts, contracts, owners, "S1")
    assert set(out["record_ref"]) == {"C1", "P001|S1"}


def test_top_alerts_sorted_by_severity_then_limited(alerts, contracts, owners):
    site = digest.alerts_for_site(alerts, contracts, owners, "S2")
    top = digest.top_alerts(site, limit=1)
    assert top["record_ref"].tolist() == ["C2"]


def test_build_digest_contains_summary_top_alerts_and_notices(alerts, contracts, owners):
    subject, text, html = digest.build_digest(
        alerts, contracts, owners, "S1", TODAY, dq_issues=62,
        dashboard_url="https://example.test/dash",
    )
    assert "Paris" in subject and "2026-11-18" in subject and "1 high" in subject
    assert "paris renewal" in text and "jakarta renewal" not in text
    assert "2 seats unused" in text
    assert "62" in text and "https://example.test/dash" in text
    assert "synthetic" in text.lower()
    assert "<table" in html and "https://example.test/dash" in html


def test_dashboard_line_omitted_when_url_missing(alerts, contracts, owners):
    _, text, _ = digest.build_digest(alerts, contracts, owners, "S1", TODAY, dq_issues=0)
    assert "Dashboard" not in text


def test_html_escapes_alert_messages(contracts, owners):
    bad = pd.DataFrame([alert("renewal_30", "C1", "high", "<script>x</script>", "C1")])
    _, _, html = digest.build_digest(bad, contracts, owners, "S1", TODAY, dq_issues=0)
    assert "<script>" not in html and "&lt;script&gt;" in html


def test_empty_site_digest_says_no_alerts(contracts, owners):
    empty = pd.DataFrame(columns=["rule", "record_ref", "contract_id", "severity", "message"])
    subject, text, _ = digest.build_digest(empty, contracts, owners, "S1", TODAY, dq_issues=0)
    assert "0 alerts" in subject and "No alerts" in text


@pytest.mark.parametrize(
    ("site_id", "when", "expected"),
    [
        ("S2", datetime(2026, 11, 18, 2, 0, tzinfo=UTC), True),
        ("S2", datetime(2026, 11, 18, 3, 0, tzinfo=UTC), False),
        ("S1", datetime(2026, 11, 18, 8, 0, tzinfo=UTC), True),
        ("S1", datetime(2026, 11, 18, 7, 0, tzinfo=UTC), False),
        ("S1", datetime(2026, 7, 15, 7, 0, tzinfo=UTC), True),
        ("S1", datetime(2026, 7, 15, 8, 0, tzinfo=UTC), False),
    ],
)
def test_should_send_only_at_nine_local_time(site_id, when, expected):
    assert digest.should_send(site_id, when) is expected


def test_recipients_prefer_site_specific_then_fallback():
    env = {"DIGEST_TO": "a@x.test, b@x.test", "DIGEST_TO_PARIS": "p@x.test"}
    assert digest.recipients("S1", env) == ["p@x.test"]
    assert digest.recipients("S2", env) == ["a@x.test", "b@x.test"]


def test_recipients_missing_raises():
    with pytest.raises(ValueError, match="DIGEST_TO"):
        digest.recipients("S1", {})


def test_smtp_settings_require_credentials():
    with pytest.raises(ValueError, match="SMTP_APP_PASSWORD"):
        digest.SmtpSettings.from_env({"SMTP_USER": "me@x.test"})
    s = digest.SmtpSettings.from_env({"SMTP_USER": "me@x.test", "SMTP_APP_PASSWORD": "pw"})
    assert (s.host, s.port) == ("smtp.gmail.com", 465)


class FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host, self.port, self.sent, self.login_args = host, port, [], None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, user, password):
        self.login_args = (user, password)

    def send_message(self, message):
        self.sent.append(message)


def test_send_email_builds_multipart_and_logs_in():
    FakeSMTP.instances.clear()
    settings = digest.SmtpSettings("smtp.test", 465, "me@x.test", "pw")
    digest.send_email("subj", "plain", "<p>html</p>", ["a@x.test", "b@x.test"], settings, FakeSMTP)
    smtp = FakeSMTP.instances[0]
    msg = smtp.sent[0]
    assert smtp.login_args == ("me@x.test", "pw")
    assert msg["Subject"] == "subj" and msg["To"] == "a@x.test, b@x.test"
    assert msg.is_multipart()


def test_name_products_replaces_known_ids_only():
    out = digest.name_products("P001 at S1 and P999", {"P001": "Microsoft 365 E3"})
    assert out == "Microsoft 365 E3 (P001) at S1 and P999"


def test_digest_shows_product_names(contracts, owners):
    a = pd.DataFrame([alert("installs_over_entitlement", "P001|S1", "high", "P001 at S1: 9 vs 5")])
    _, text, _ = digest.build_digest(
        a, contracts, owners, "S1", TODAY, 0, product_names={"P001": "Microsoft 365 E3"}
    )
    assert "Microsoft 365 E3 (P001) at S1" in text
