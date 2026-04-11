# NiaHealth Mentions Monitor

Monitors free, publicly available sources for NiaHealth brand mentions and posts formatted alerts to `#niahealth-mentions` in Slack. Runs on GitHub Actions every 15 minutes at zero ongoing cost.

## Sources

| Source | Method | Cost |
|---|---|---|
| Google News RSS | RSS via `feedparser` | Free |
| Google Alerts RSS | RSS via `feedparser` | Free |
| Reddit | Public JSON API (no auth) | Free |
| Hacker News | Algolia HN Search API | Free |
| NewsData.io | REST API (free tier, 200 credits/day) | Free |

## Setup

### 1. GitHub repo secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `SLACK_WEBHOOK_URL` | Incoming Webhook URL for `#niahealth-mentions` |
| `NEWSDATA_API_KEY` | Free-tier API key from [newsdata.io](https://newsdata.io) |

### 2. Google Alerts (optional)

Create Google Alerts for each keyword, select "RSS feed" as delivery, and add the feed URLs to `config.yaml` under `sources.google_alerts.feed_urls`.

### 3. Enable the workflow

Push the code. The workflow runs automatically every 15 minutes, or trigger manually from **Actions → Social Media Monitor → Run workflow**.

## Running locally

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export NEWSDATA_API_KEY="your-key-here"

pip install -r social-monitor/requirements.txt
python social-monitor/monitor.py
```

Set `DRY_RUN=1` to see output without posting to Slack:

```bash
DRY_RUN=1 python social-monitor/monitor.py
```

## Configuration

Edit `config.yaml` to adjust keywords, enable/disable sources, or change dedup TTL. No code changes needed.

## Architecture

```
social-monitor/
├── monitor.py              # Async orchestrator
├── sources/
│   ├── google_news.py      # Google News RSS adapter
│   ├── google_alerts.py    # Google Alerts RSS adapter
│   ├── reddit.py           # Reddit JSON API adapter
│   ├── hackernews.py       # Algolia HN Search adapter
│   └── newsdata.py         # NewsData.io API adapter
├── slack_poster.py         # Formats + posts Slack Block Kit messages
├── dedup.py                # Title/URL hashing with TTL-based pruning
├── config.yaml             # Keywords, sources, settings
├── seen.json               # Dedup state (committed back after each run)
└── requirements.txt
```

Each run: fetch all sources in parallel → deduplicate → post new mentions to Slack → commit `seen.json`.
