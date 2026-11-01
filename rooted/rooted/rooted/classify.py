"""Rule based tagging. Rules first; swap in a model once there is a labeled set to test it against."""
from __future__ import annotations

import re

# Order matters: the first family whose pattern matches the title wins.
ROLE_FAMILIES = [
    ("Trades", r"\b(electrician|installer|technician|lineman|lineworker|apprentice|hvac|crew lead|foreman)\b"),
    ("Sales", r"\b(account executive|sales|business development|bdr|sdr|partnerships?|account manager|customer success|development (associate|director|officer))\b"),
    ("Finance", r"\b(finance|financial|accountant|accounting|controller|fp&a|treasury|grants?)\b"),
    ("Data", r"\b(data|analytics|analyst|scientist|gis)\b"),
    ("Engineering", r"\b(engineer|developer|software|firmware|devops|architect)\b"),
    ("Marketing", r"\b(marketing|growth|communications|content|brand|outreach|community)\b"),
    ("Policy", r"\b(policy|regulatory|government affairs|advocacy|advocate|legislative)\b"),
    ("Operations", r"\b(operations|project (manager|coordinator)|program manager|supply chain|logistics|procurement|coordinator|people|recruit)\b"),
]

# Phrases that signal the employer wants prior climate or energy industry experience.
REQUIRES_CLIMATE = re.compile(
    r"(\d\+?\s*years?[^.]{0,60}(renewable|clean ?energy|solar|utility|utilities|energy (industry|sector)|climate|sustainability))"
    r"|((experience|background) (in|with) (the )?(renewable|clean ?energy|solar|utility|utilities|energy|climate|sustainability))",
    re.I,
)

METROS = {
    "rdu": ["raleigh", "durham", "cary", "chapel hill", "morrisville", "research triangle", "rtp", "apex", "wake forest", "pittsboro"],
}


def role_family(title: str) -> str:
    t = title.lower()
    for family, pattern in ROLE_FAMILIES:
        if re.search(pattern, t):
            return family
    return "Other"


def needs_climate_background(description: str) -> bool:
    return bool(REQUIRES_CLIMATE.search(description or ""))


def metro(location: str) -> str | None:
    loc = (location or "").lower()
    for key, words in METROS.items():
        if any(w in loc for w in words):
            return key
    return None


def tag(job: dict) -> dict:
    job["family"] = role_family(job["title"])
    job["no_climate_background"] = not needs_climate_background(job.get("description", ""))
    job["metro"] = metro(job.get("location", ""))
    return job
