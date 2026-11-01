"""Fetch and normalize postings from public job board APIs.

Each adapter turns one provider's JSON into a list of Job dicts with the same keys:
    uid, employer, title, location, remote, pay, url, posted_at, description, source
"""
from __future__ import annotations

import html
import json
import re
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "RootedJobsBot/0.1 (+https://example.com/about)"

ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true",
}


def fetch_json(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def strip_html(raw: str) -> str:
    text = html.unescape(raw or "")          # Greenhouse double encodes its HTML
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _iso_from_ms(ms) -> str | None:
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()


def _money(n) -> str:
    if n is None:
        return ""
    return f"${n / 1000:.0f}k" if n >= 1000 else f"${n:,.0f}"


def normalize_greenhouse(data: dict, employer_id: str) -> list[dict]:
    jobs = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        jobs.append({
            "uid": f"greenhouse:{employer_id}:{j['id']}",
            "employer": employer_id,
            "title": j.get("title", "").strip(),
            "location": loc,
            "remote": "remote" in loc.lower(),
            "pay": "",                                   # Greenhouse public board rarely exposes pay
            "url": j.get("absolute_url", ""),
            "posted_at": j.get("first_published") or j.get("updated_at"),
            "description": strip_html(j.get("content", "")),
            "source": "Greenhouse",
        })
    return jobs


def normalize_lever(data: list, employer_id: str) -> list[dict]:
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        loc = cats.get("location", "") or ""
        sr = j.get("salaryRange") or {}
        pay = ""
        if sr.get("min") or sr.get("max"):
            pay = f"{_money(sr.get('min'))} to {_money(sr.get('max'))}".strip()
        jobs.append({
            "uid": f"lever:{employer_id}:{j['id']}",
            "employer": employer_id,
            "title": (j.get("text") or "").strip(),
            "location": loc,
            "remote": j.get("workplaceType") == "remote" or "remote" in loc.lower(),
            "pay": pay,
            "url": j.get("hostedUrl", ""),
            "posted_at": _iso_from_ms(j.get("createdAt")),
            "description": j.get("descriptionPlain") or strip_html(j.get("description", "")),
            "source": "Lever",
        })
    return jobs


def normalize_ashby(data: dict, employer_id: str) -> list[dict]:
    jobs = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        comp = j.get("compensation") or {}
        pay = comp.get("scrapeableCompensationSalarySummary") or comp.get("compensationTierSummary") or ""
        loc = j.get("location", "") or ""
        jobs.append({
            "uid": f"ashby:{employer_id}:{j['id']}",
            "employer": employer_id,
            "title": (j.get("title") or "").strip(),
            "location": loc,
            "remote": bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
            "pay": pay,
            "url": j.get("jobUrl", ""),
            "posted_at": j.get("publishedAt"),
            "description": j.get("descriptionPlain") or strip_html(j.get("descriptionHtml", "")),
            "source": "Ashby",
        })
    return jobs


NORMALIZERS = {"greenhouse": normalize_greenhouse, "lever": normalize_lever, "ashby": normalize_ashby}


def fetch_employer(employer: dict, fetch=fetch_json) -> list[dict]:
    """Fetch one employer's board. `fetch` is injectable so tests run offline."""
    ats, slug = employer["ats"], employer["slug"]
    if ats == "manual":
        return [dict(j, employer=employer["id"], source="Manual entry") for j in employer.get("manual_jobs", [])]
    data = fetch(ENDPOINTS[ats].format(slug=slug))
    return NORMALIZERS[ats](data, employer["id"])
