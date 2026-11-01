# Rooted

Climate jobs for people who are not in climate yet. A daily job pulls listings from employers' public job boards, tags each role, and publishes a static search site.

## How it works

1. `data/employers.json` is the curated employer list: name, ATS, board slug, impact area, and a plain English description. This list is the real product asset.
2. `python -m rooted.ingest` fetches each employer's public board (Greenhouse, Lever or Ashby), normalizes every posting to one shape, and tags it:
   * role family from the title (Sales, Operations, Finance, Data, Engineering, Marketing, Policy, Trades)
   * whether the posting asks for prior climate or energy experience
   * metro (Raleigh Durham to start) and remote
3. Freshness: each job keeps `first_seen` and `last_seen`. A job missing from its board for 48 hours is removed. A board that errors out keeps its jobs until they go stale, so one outage does not wipe an employer.
4. Output goes to `site/data/jobs.json` and `site/data/employers.json`. `site/index.html` is a static page that loads those two files. No server, no database.
5. A GitHub Action runs the whole thing daily and deploys to GitHub Pages for free.

## Run it locally

Python 3.10 or newer, no dependencies.

    python -m unittest discover -s tests -t .
    python -m rooted.check data/employers.json      # confirm each board slug works
    python -m rooted.ingest --employers data/employers.json --out site/data
    python -m http.server -d site 8000              # open http://localhost:8000

## Adding an employer

Find the board slug in the employer's careers link:

| ATS | Careers URL looks like | Slug |
| --- | --- | --- |
| Greenhouse | job-boards.greenhouse.io/**slug** | slug |
| Lever | jobs.lever.co/**slug** | slug |
| Ashby | jobs.ashbyhq.com/**slug** | slug |

Add an entry to `data/employers.json`, then run `python -m rooted.check`. Employers on Workday or custom pages use `"ats": "manual"` with a `manual_jobs` list until a better source exists.

The three starter slugs in `data/employers.json` are unverified guesses. Run the check before relying on them.

## Deploy

1. Push this folder to a new GitHub repo.
2. Settings, Pages, Source: GitHub Actions.
3. Actions tab, run "Refresh listings and publish site" once by hand. After that it runs daily.

## Ground rules

* Only read published public board endpoints. Never scrape pages behind a login or against a site's terms.
* Every apply button links to the employer's own page.
* Do not use ATS vendor logos as the product's brand.

## Next up

* Weekly email alerts for a saved search (Buttondown or Resend plus a second scheduled job)
* Employer intake form for manual listings
* Click tracking per employer, to show value before charging
* Swap the title rules for a model once there is a hand labeled set to test it against
