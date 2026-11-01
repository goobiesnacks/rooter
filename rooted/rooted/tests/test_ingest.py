"""Offline tests. Fixtures mirror the documented public response shape of each provider."""
import unittest
from datetime import datetime, timedelta, timezone

from rooted.classify import metro, needs_climate_background, role_family
from rooted.ingest import run

GREENHOUSE = {"jobs": [{
    "id": 101, "title": "Account Executive, Utilities", "absolute_url": "https://boards.greenhouse.io/x/jobs/101",
    "location": {"name": "Durham, NC"}, "updated_at": "2026-10-30T12:00:00-04:00",
    "content": "&lt;p&gt;Sell to utilities. 3+ years of B2B SaaS sales.&lt;/p&gt;"}]}
LEVER = [{
    "id": "abc", "text": "Commercial Electrician", "hostedUrl": "https://jobs.lever.co/y/abc",
    "categories": {"location": "Raleigh, NC", "commitment": "Full-time"}, "workplaceType": "onsite",
    "createdAt": 1793500000000, "salaryRange": {"min": 62000, "max": 85000, "currency": "USD", "interval": "per-year-salary"},
    "descriptionPlain": "Requires 2+ years of experience in solar installation."}]
ASHBY = {"jobs": [
    {"id": "z1", "title": "Senior Software Engineer", "location": "Remote", "isRemote": True, "isListed": True,
     "jobUrl": "https://jobs.ashbyhq.com/z/z1", "publishedAt": "2026-10-28T00:00:00Z",
     "descriptionPlain": "Build data pipelines.",
     "compensation": {"scrapeableCompensationSalarySummary": "$160K - $195K"}},
    {"id": "z2", "title": "Hidden role", "location": "Remote", "isListed": False, "jobUrl": "", "descriptionPlain": ""}]}

EMPLOYERS = [
    {"id": "gh", "ats": "greenhouse", "slug": "x"},
    {"id": "lv", "ats": "lever", "slug": "y"},
    {"id": "ab", "ats": "ashby", "slug": "z"},
]


def fake_fetch(url):
    if "greenhouse" in url:
        return GREENHOUSE
    if "lever" in url:
        return LEVER
    if "ashby" in url:
        return ASHBY
    raise AssertionError(url)


NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


class TestIngest(unittest.TestCase):
    def test_normalizes_all_three_sources(self):
        jobs, errors = run(EMPLOYERS, {}, NOW, fetch=fake_fetch)
        self.assertEqual(errors, [])
        self.assertEqual(len(jobs), 3)  # unlisted Ashby role skipped
        gh = jobs["greenhouse:gh:101"]
        self.assertEqual(gh["family"], "Sales")
        self.assertEqual(gh["metro"], "rdu")
        self.assertTrue(gh["no_climate_background"])
        self.assertNotIn("<p>", gh["description"])
        lv = jobs["lever:lv:abc"]
        self.assertEqual(lv["family"], "Trades")
        self.assertEqual(lv["pay"], "$62k to $85k")
        self.assertFalse(lv["no_climate_background"])
        ab = jobs["ashby:ab:z1"]
        self.assertTrue(ab["remote"])
        self.assertEqual(ab["family"], "Engineering")

    def test_first_seen_kept_and_stale_jobs_dropped(self):
        first, _ = run(EMPLOYERS, {}, NOW, fetch=fake_fetch)
        later = NOW + timedelta(hours=24)
        second, _ = run(EMPLOYERS, first, later, fetch=fake_fetch)
        self.assertEqual(second["greenhouse:gh:101"]["first_seen"], NOW.isoformat())
        self.assertEqual(second["greenhouse:gh:101"]["last_seen"], later.isoformat())

        def lever_gone(url):
            return [] if "lever" in url else fake_fetch(url)
        kept, _ = run(EMPLOYERS, second, later + timedelta(hours=24), fetch=lever_gone)
        self.assertIn("lever:lv:abc", kept)        # missing 24h: kept
        dropped, _ = run(EMPLOYERS, kept, later + timedelta(hours=49), fetch=lever_gone)
        self.assertNotIn("lever:lv:abc", dropped)  # missing over 48h: removed

    def test_broken_board_does_not_stop_run(self):
        def flaky(url):
            if "lever" in url:
                raise TimeoutError("board down")
            return fake_fetch(url)
        jobs, errors = run(EMPLOYERS, {}, NOW, fetch=flaky)
        self.assertEqual(len(jobs), 2)
        self.assertEqual(errors[0]["employer"], "lv")

    def test_manual_entry(self):
        emp = {"id": "lt", "ats": "manual", "slug": "", "manual_jobs": [{
            "uid": "manual:lt:1", "title": "Development Associate", "location": "Pittsboro, NC",
            "remote": False, "pay": "", "url": "https://example.org", "posted_at": "2026-11-01", "description": ""}]}
        jobs, _ = run([emp], {}, NOW, fetch=fake_fetch)
        self.assertEqual(jobs["manual:lt:1"]["family"], "Sales")
        self.assertEqual(jobs["manual:lt:1"]["source"], "Manual entry")


class TestClassify(unittest.TestCase):
    def test_families(self):
        cases = {
            "Sales Development Representative": "Sales",
            "Heat Pump Installer": "Trades",
            "Emissions Data Analyst": "Data",
            "Project Finance Analyst": "Finance",
            "Growth Marketing Manager": "Marketing",
            "Installation Project Coordinator": "Operations",
            "Battery Logistics Manager": "Operations",
            "Climate Policy Fellow": "Policy",
        }
        for title, want in cases.items():
            self.assertEqual(role_family(title), want, title)

    def test_background_and_metro(self):
        self.assertTrue(needs_climate_background("5+ years of experience in the renewable energy industry"))
        self.assertFalse(needs_climate_background("3+ years of B2B sales experience"))
        self.assertEqual(metro("Remote, US"), None)
        self.assertEqual(metro("Chapel Hill, NC"), "rdu")


if __name__ == "__main__":
    unittest.main()
