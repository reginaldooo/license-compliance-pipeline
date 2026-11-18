"""Spreadsheet-style noise: messy product names and mixed date formats."""

from datetime import date

import numpy as np

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MIN_TYPO_LEN = 10

ALIASES = {
    "P001": ("M365 E3", "Office 365 E3", "MS 365 E3"),
    "P002": ("Visio P2", "Microsoft Visio Plan 2"),
    "P003": ("MS Project P3", "Project Online Plan 3"),
    "P004": ("Acrobat Pro DC", "Adobe Acrobat Professional"),
    "P005": ("Autodesk AutoCAD 2024", "AutoCAD (full)"),
    "P006": ("CATIA V5-6R2022", "Catia V5"),
    "P007": ("SolidWorks Pro", "SOLIDWORKS Premium"),
    "P008": ("ANSYS Mech", "Ansys Mechanical Enterprise"),
    "P009": ("MATLAB R2024b", "Matlab (Mathworks)"),
    "P010": ("NX CAD", "Siemens NX 2306"),
    "P011": ("Oracle DB EE", "Oracle Database 19c EE"),
    "P012": ("vSphere Ent Plus", "VMware vSphere Enterprise"),
    "P013": ("JIRA", "Atlassian Jira Software Cloud"),
    "P014": ("Confluence Cloud", "Atlassian Confluence"),
    "P015": ("Slack Business Plus", "Slack BIZ+"),
    "P016": ("Copilot Business (GitHub)", "GH Copilot Business"),
    "P017": ("M365 Copilot", "Microsoft 365 Copilot"),
    "P018": ("ChatGPT for Teams", "OpenAI ChatGPT Team"),
}

UNMAPPED_NAMES = (
    "Zorbex CAD Suite",
    "Legacy Reporting Tool v2",
    "Internal HR Portal client",
    "Quantum Sim Lite",
    "OpenTool Free Edition",
    "Acme Fleet Manager",
)


def _swap_adjacent(name: str, rng: np.random.Generator) -> str:
    if len(name) < MIN_TYPO_LEN:
        return name
    i = int(rng.integers(1, len(name) - 2))
    return name[:i] + name[i + 1] + name[i] + name[i + 2 :]


def _drop_char(name: str, rng: np.random.Generator) -> str:
    i = int(rng.integers(1, len(name) - 1))
    return name[:i] + name[i + 1 :]


def _double_char(name: str, rng: np.random.Generator) -> str:
    i = int(rng.integers(1, len(name) - 1))
    return name[: i + 1] + name[i] + name[i + 1 :]


def messy_name(
    product_id: str, catalog_name: str, rng: np.random.Generator, harsh: bool = False
) -> str:
    """Return a spreadsheet-style variant of a catalog product name."""
    style = int(rng.integers(0, 13 if harsh else 7))
    aliases = ALIASES[product_id]
    if style == 7:
        return catalog_name.replace(" ", "")
    if style == 8:
        return catalog_name.replace(" ", "-")
    if style == 9:
        return _drop_char(catalog_name, rng)
    if style == 10:
        return _double_char(catalog_name, rng)
    if style == 11:
        alias = str(aliases[int(rng.integers(len(aliases)))])
        return f"{alias} v{int(rng.integers(1, 30))}.{int(rng.integers(0, 10))}"
    if style == 12:
        return catalog_name[: max(len(catalog_name) // 2 + 3, 8)]
    if style == 1:
        return catalog_name.lower()
    if style == 2:
        return catalog_name.upper()
    if style in (3, 4):
        return str(aliases[int(rng.integers(len(aliases)))])
    if style == 5:
        return _swap_adjacent(catalog_name, rng)
    if style == 6:
        return f"  {catalog_name} (x64) "
    return catalog_name


def format_date(value: date | str, rng: np.random.Generator, extra: bool = False) -> str:
    """Render a date in one of three formats (five when extra). Strings pass through."""
    if isinstance(value, str):
        return value
    style = int(rng.integers(0, 5 if extra else 3))
    if style == 3:
        return f"{MONTHS[value.month - 1]} {value.day}, {value.year}"
    if style == 4:
        return value.strftime("%Y/%m/%d")
    if style == 0:
        return value.isoformat()
    if style == 1:
        return value.strftime("%d/%m/%Y")
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"
