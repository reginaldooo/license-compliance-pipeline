"""Daily digest: pick a site's top alerts, render text and HTML, send by SMTP."""

import html
import re
import smtplib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pandas as pd

from . import config

SEND_HOUR = 9
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
ORG_WIDE_RULES = frozenset({"seat_unused_90d"})
DEFAULT_TOP_N = 10
NOTICE = "All data is synthetic and generated for a portfolio project."


def _alert_site(row, site_by_contract: dict[str, str]) -> str | None:
    if isinstance(row.contract_id, str):
        return site_by_contract.get(row.contract_id)
    if "|" in row.record_ref:
        return row.record_ref.split("|")[1]
    return None


def alerts_for_site(
    alerts: pd.DataFrame, contracts: pd.DataFrame, owners: pd.DataFrame, site_id: str
) -> pd.DataFrame:
    """Alerts tied to a site through the contract owner or a product|site reference."""
    sited = contracts.merge(owners[["owner_id", "site_id"]], on="owner_id")
    site_by_contract = dict(zip(sited["contract_id"], sited["site_id"], strict=True))
    keep = [_alert_site(row, site_by_contract) == site_id for row in alerts.itertuples()]
    return alerts.loc[keep]


def name_products(message: str, product_names: Mapping[str, str]) -> str:
    """Replace product ids with names: 'P004' becomes 'Adobe Acrobat Pro (P004)'.

    An id already inside parentheses becomes the plain name, so no parentheses nest.
    """

    def replace(match: re.Match[str]) -> str:
        pid = match.group("pid")
        name = product_names.get(pid)
        if name is None:
            return match.group()
        return f"({name})" if match.group("open") else f"{name} ({pid})"

    return re.sub(r"(?P<open>\()?\b(?P<pid>P\d{3})\b(?(open)\))", replace, message)


def top_alerts(alerts: pd.DataFrame, limit: int = DEFAULT_TOP_N) -> pd.DataFrame:
    order = alerts["severity"].map(SEVERITY_ORDER)
    ranked = alerts.assign(_rank=order).sort_values(["_rank", "rule", "record_ref"])
    return ranked.drop(columns="_rank").head(limit)


def build_digest(
    alerts: pd.DataFrame,
    contracts: pd.DataFrame,
    owners: pd.DataFrame,
    site_id: str,
    today: date,
    dq_issues: int,
    dashboard_url: str | None = None,
    top_n: int = DEFAULT_TOP_N,
    product_names: Mapping[str, str] | None = None,
    scenario_name: str | None = None,
) -> tuple[str, str, str]:
    """Return (subject, plain text, html) for one site."""
    site_name = config.SITES[site_id][0]
    mine = alerts_for_site(alerts, contracts, owners, site_id)
    idle_seats = int(alerts["rule"].isin(ORG_WIDE_RULES).sum())
    n_high = int((mine["severity"] == "high").sum())
    subject = f"[License digest] {site_name} {today.isoformat()}: {n_high} high, {len(mine)} alerts"
    by_rule = mine.groupby("rule").size().sort_index()
    top = top_alerts(mine, top_n)
    top = top.assign(message=[name_products(m, product_names or {}) for m in top["message"]])

    text = [f"License renewal and compliance digest: {site_name}, {today.isoformat()}", ""]
    if mine.empty:
        text += ["No alerts for this site today."]
    else:
        text += ["Summary", *[f"- {rule}: {n}" for rule, n in by_rule.items()], ""]
        text += [f"Top {len(top)} alerts"]
        text += [f"{i}. [{r.severity}] {r.message}" for i, r in enumerate(top.itertuples(), 1)]
    text += ["", f"Org-wide: {idle_seats} seats unused for more than {config.UNUSED_DAYS} days."]
    text += [f"Data quality: {dq_issues} open issues."]
    if dashboard_url:
        text += [f"Dashboard: {dashboard_url}"]
    if scenario_name:
        text += [f"Data scenario today: {scenario_name}."]
    text += ["", NOTICE]

    rows = "".join(
        f"<tr><td>{html.escape(r.severity)}</td><td>{html.escape(r.rule)}</td>"
        f"<td>{html.escape(r.message)}</td></tr>"
        for r in top.itertuples()
    )
    link = (
        f'<p><a href="{html.escape(dashboard_url, quote=True)}">Open the dashboard</a>'
        f" ({html.escape(dashboard_url)})</p>"
        if dashboard_url
        else ""
    )
    body = (
        "<p>No alerts for this site today.</p>"
        if mine.empty
        else f"<table border='1' cellpadding='4'><tr><th>Severity</th><th>Rule</th>"
        f"<th>Alert</th></tr>{rows}</table>"
    )
    scenario_html = (
        f"<p>Data scenario today: {html.escape(scenario_name)}.</p>" if scenario_name else ""
    )
    page = (
        f"<h2>License digest: {html.escape(site_name)}, {today.isoformat()}</h2>{body}"
        f"<p>Org-wide: {idle_seats} seats unused for more than {config.UNUSED_DAYS} days. "
        f"Data quality: {dq_issues} open issues.</p>{link}{scenario_html}<p><i>{NOTICE}</i></p>"
    )
    return subject, "\n".join(text), page


def should_send(site_id: str, now: datetime) -> bool:
    """True when it is 09:00 local time at the site. Handles daylight saving time."""
    return now.astimezone(ZoneInfo(config.SITES[site_id][1])).hour == SEND_HOUR


def recipients(site_id: str, env: Mapping[str, str]) -> list[str]:
    site_key = f"DIGEST_TO_{config.SITES[site_id][0].upper()}"
    raw = env.get(site_key) or env.get("DIGEST_TO") or ""
    found = [part.strip() for part in raw.split(",") if part.strip()]
    if not found:
        raise ValueError(f"set {site_key} or DIGEST_TO to at least one address")
    return found


@dataclass(frozen=True)
class SmtpSettings:
    host: str
    port: int
    user: str
    password: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "SmtpSettings":
        missing = [k for k in ("SMTP_USER", "SMTP_APP_PASSWORD") if not env.get(k)]
        if missing:
            raise ValueError(f"missing environment variables: {', '.join(missing)}")
        return cls(
            env.get("SMTP_HOST", "smtp.gmail.com"),
            int(env.get("SMTP_PORT", "465")),
            env["SMTP_USER"],
            env["SMTP_APP_PASSWORD"],
        )


def send_email(
    subject: str,
    text: str,
    html_body: str,
    to: list[str],
    settings: SmtpSettings,
    smtp_factory=smtplib.SMTP_SSL,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.user
    message["To"] = ", ".join(to)
    message.set_content(text)
    message.add_alternative(html_body, subtype="html")
    with smtp_factory(settings.host, settings.port) as smtp:
        smtp.login(settings.user, settings.password)
        smtp.send_message(message)
