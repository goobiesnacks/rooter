"""Daily run: fetch every employer, tag jobs, track freshness, write the site's data files.

Usage:
    python -m rooted.ingest --employers data/employers.json --out site/data
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .classify import tag
from .sources import fetch_employer, fetch_json

STALE_AFTER = timedelta(hours=48)


def merge(previous: dict[str, dict], fresh: list[dict], now: datetime) -> dict[str, dict]:
    """Keep first_seen from earlier runs, stamp last_seen now, drop jobs unseen for 48h."""
    stamp = now.isoformat()
    merged: dict[str, dict] = {}
    for job in fresh:
        old = previous.get(job["uid"], {})
        job["first_seen"] = old.get("first_seen", stamp)
        job["last_seen"] = stamp
        merged[job["uid"]] = job
    for uid, old in previous.items():
        if uid in merged:
            continue
        if now - datetime.fromisoformat(old["last_seen"]) < STALE_AFTER:
            merged[uid] = old          # board hiccup: keep it until it has been missing 48h
    return merged


def run(employers: list[dict], previous: dict[str, dict], now: datetime, fetch=fetch_json):
    fresh, errors = [], []
    for emp in employers:
        try:
            jobs = fetch_employer(emp, fetch=fetch)
            fresh.extend(tag(j) for j in jobs)
        except Exception as exc:  # one broken board must not stop the run
            errors.append({"employer": emp["id"], "error": f"{type(exc).__name__}: {exc}"})
            # keep that employer's existing jobs alive until they go stale
    return merge(previous, fresh, now), errors


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--employers", default="data/employers.json")
    p.add_argument("--out", default="site/data")
    args = p.parse_args(argv)

    employers = json.loads(Path(args.employers).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    jobs_path = out / "jobs.json"
    previous = {}
    if jobs_path.exists():
        previous = {j["uid"]: j for j in json.loads(jobs_path.read_text())["jobs"]}

    now = datetime.now(timezone.utc)
    jobs, errors = run(employers, previous, now)

    public_employers = {e["id"]: {k: e[k] for k in ("name", "impact", "what", "why") if k in e} for e in employers}
    jobs_path.write_text(json.dumps({
        "generated_at": now.isoformat(),
        "jobs": sorted(jobs.values(), key=lambda j: j["first_seen"], reverse=True),
    }, indent=1))
    (out / "employers.json").write_text(json.dumps(public_employers, indent=1))

    print(f"{len(jobs)} jobs from {len(employers)} employers, {len(errors)} errors")
    for e in errors:
        print(f"  {e['employer']}: {e['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
