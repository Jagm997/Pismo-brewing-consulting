# Pismo Brewing — Alcohol Consumption Trend Digest

Monitors California & U.S. alcohol consumption trends via Google News RSS,
analyzes them with Claude, and emails a top-5 trend digest every Monday at
9:00 AM Pacific Time.

This is a v1 built for a single craft brewery (no competitor tracking) —
each week it scans recent news across three topic areas and picks the 5
trends most relevant to Pismo Brewing's business.

---

## Files

| File | Purpose |
|------|---------|
| `config.py` | RSS topic queries + Claude system prompt |
| `fetch_intel.py` | Main script: fetches RSS → Claude analysis → saves JSON → emails digest |
| `app.py` | Optional Streamlit dashboard reading `trend_digest.json` |
| `trend_digest.json` | Output file (committed by GitHub Actions after each run) |
| `.github/workflows/intel_schedule.yml` | GitHub Actions cron schedule (Monday 9am PT) |

---

## Setup

### 1. Install

```bash
cd pismo-intel-agent
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Anthropic API key and Gmail app password
```

### 3. Run manually

```bash
python fetch_intel.py            # full run
python fetch_intel.py --dry-run  # fetch feeds only, no Claude call, no email
python fetch_intel.py --hours 336  # extend lookback to 14 days
```

### 4. Launch the dashboard (optional)

```bash
streamlit run app.py
```

### 5. Set up GitHub Actions (for the automatic Monday run)

Add these as **repository secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `EMAIL_FROM` | Gmail address to send from |
| `EMAIL_TO` | Address(es) to receive the digest, comma-separated |
| `EMAIL_PASSWORD` | Gmail App Password (not your account password) |

Email is optional — the workflow will still run and commit `trend_digest.json`
without it.

The schedule runs Monday at 9:00 AM Pacific Time year-round. Since GitHub
Actions cron is UTC-only and doesn't adjust for daylight saving, the workflow
fires at both 16:00 and 17:00 UTC and uses a guard step that checks the actual
Pacific hour and skips the run that doesn't match. See the comments in
`intel_schedule.yml` for details.

---

## Gmail setup

Gmail requires an App Password when 2FA is enabled (which it should be):

1. Go to https://myaccount.google.com/apppasswords
2. Create a new app password for "Mail"
3. Use that 16-character password as `EMAIL_PASSWORD`

---

## RSS sources

Each topic in `config.py` combines direct RSS feeds (high-signal, reputable
sources) with broader Google News RSS searches (catch-all coverage). Direct
feeds currently wired in:

| Source | Feed | Topic |
|--------|------|-------|
| Brewers Association | `brewersassociation.org/feed/` | Craft Beer & Brewery Industry |
| Brewbound | `brewbound.com/feed` | Craft Beer & Brewery Industry |
| VinePair (Booze News) | `vinepair.com/booze-news/feed` | Consumer Behavior & Preferences |
| CA Dept. of Alcoholic Beverage Control | `abc.ca.gov/feed/` | Overall Alcohol Consumption Trends |
| New Times SLO | `newtimesslo.com/feed` | Central Coast / Local Market |

New Times SLO is a general Central Coast alt-weekly, not alcohol-specific —
the Claude prompt is instructed to ignore unrelated local news and only pull
trends relevant to alcohol, brewing, or the local visitor economy from it.

Some other reputable sources (CGA/NIQ, IWSR, NIAAA) don't publish public RSS
feeds and would require a paid data feed or manual monitoring — not included
in v1.

---

## Customizing

**Change what's monitored:**
Edit `TOPICS` in `config.py` — each topic has a `feeds` list (direct RSS) and
a `google_news_queries` list (Google News searches). Add, remove, or reword
either to shift what the digest surfaces.

**Change how many trends / the schema:**
Edit `TREND_SYSTEM` in `config.py`.

**Change the schedule:**
Edit the `cron` lines in `.github/workflows/intel_schedule.yml`.

---

## Possible v2 ideas

- Add a paid data feed (CGA/NIQ, IWSR) if budget allows, for hard consumption
  numbers rather than news coverage
- Track trend history over time (which trends recur / are accelerating)
- Second weekly digest slot, or on-demand Slack trigger
