# NiaHealth Mentions Monitor — Technical Specification

**Version 1.0 — April 2026**

Phase 1: `#niahealth-mentions` Slack Channel

Hosted on GitHub · Scheduled via GitHub Actions · Written in Python

---

## 1. Overview

This spec defines the first phase of a social media and news monitoring system for NiaHealth, a Canadian health care technology company. The system monitors free, publicly available sources for brand mentions, deduplicates results, and posts formatted alerts to a dedicated Slack channel in near real-time.

The goal is maximum coverage at zero ongoing cost, running entirely on GitHub Actions with no paid APIs or third-party SaaS subscriptions required.

---

## 2. What We Monitor

The monitor tracks all public mentions of NiaHealth across six source categories. Each source was chosen because it is free, offers programmatic access, and can be polled at intervals of 15 minutes or less.

### 2.1 Source Matrix

| Source | Method | Cost | Latency |
|---|---|---|---|
| Google News RSS | RSS feed via `feedparser` | Free | ~5–15 min from publish |
| Google Alerts RSS | RSS feed via `feedparser` | Free | ~15–60 min from publish |
| Reddit | JSON API (no auth needed for search) | Free | ~5–15 min (poll interval) |
| Hacker News | Algolia HN Search API | Free | ~1–5 min (indexed fast) |
| F5Bot | Email alerts → parsed or webhook | Free | ~2–5 min from post |
| NewsData.io API | REST API (free tier) | Free (200 credits/day) | Near real-time |

### 2.2 Source Details

#### Google News RSS

Google News aggregates thousands of publishers and exposes results as RSS. This is the single highest-value free source for news coverage. The monitor hits a URL like:

```
https://news.google.com/rss/search?q="NiaHealth"+OR+"Nia+Health"&hl=en-CA&gl=CA&ceid=CA:en
```

The Canadian locale parameters (`hl`, `gl`, `ceid`) bias results toward Canadian outlets while still including international coverage. The feed is parsed with Python's `feedparser` library. Each entry provides a title, link, source name, and publish timestamp.

#### Google Alerts RSS

Google Alerts can deliver results via RSS rather than email. Set up alerts for each keyword variant ("NiaHealth", "Nia Health", founder names, product names) and select "RSS feed" as the delivery method. These feeds catch long-tail sources that Google News sometimes misses, including blogs, niche publications, and press release wires.

#### Reddit

Reddit's public JSON API allows unauthenticated search across all subreddits. The endpoint `https://www.reddit.com/search.json?q=NiaHealth&sort=new&limit=25` returns recent posts mentioning the keyword. No OAuth or API key is required for read-only search, and the free rate limit of 60 requests per minute is far more than sufficient for a monitor polling every 15 minutes. This covers all of Reddit, not just specific subreddits, so mentions in unexpected communities are still caught.

#### Hacker News (Algolia API)

Hacker News is indexed in near real-time by Algolia's free HN Search API at `hn.algolia.com/api/v1/search_by_date`. This is relevant because health tech stories, funding announcements, and Canadian startup news frequently surface on HN. The API supports filtering by timestamp, so the monitor only requests items newer than the last check.

#### F5Bot

F5Bot is a free service that monitors Reddit, Hacker News, and Lobsters for keyword mentions and sends email alerts within minutes. It acts as a safety net — if the direct Reddit or HN polling misses something, F5Bot catches it. The free tier supports keyword tracking with no credit card required. Alerts arrive via email; the monitor can either parse these via a connected Gmail account or, for simplicity, use F5Bot's paid webhook option to post directly to Slack. The free email path is recommended for v1.

#### NewsData.io API

NewsData.io aggregates news from thousands of sources in 89+ languages and offers a free tier of 200 API credits per day. Each request returns structured JSON with title, description, source, and publish date. The free tier is enough for hourly polling with keyword searches. This supplements Google News by providing access to sources that may not appear in Google's RSS feed, particularly international health tech outlets and wire services.

### 2.3 Search Keywords

The following keywords are monitored. All matching is case-insensitive. The config file allows easy addition of new terms without code changes.

- **"NiaHealth"** — exact brand name
- **"Nia Health"** — spaced variant
- **Founder and executive names** — configure in `config.yaml`
- **Product or service names** — as they become public
- **"niahealth.com"** — catches link shares

---

## 3. Near Real-Time Strategy

Achieving near real-time monitoring for free requires layering multiple polling intervals and leveraging services that already do the heavy lifting of crawling.

### 3.1 Polling Schedule

The GitHub Actions workflow runs on a cron schedule every 15 minutes. This is the core heartbeat of the system. Each run takes roughly 30–60 seconds, which is well within GitHub Actions' free tier of 2,000 minutes per month for private repos. At 15-minute intervals, the monitor uses approximately 96 runs per day, each lasting under 1 minute, totaling around 2,880 minutes per month. This fits comfortably within the free tier if the repo is public (unlimited minutes). For private repos, reduce polling to every 20 minutes (~1,620 min/month) to stay under the limit.

### 3.2 Effective Latency

The end-to-end latency from an article being published to it appearing in Slack is determined by two factors: how quickly the source indexes the content, and the polling interval. In practice, most mentions reach Slack within 5–30 minutes of publication. Google News RSS indexes major outlets within minutes; smaller blogs may take up to an hour. Reddit and HN posts are available instantly via their APIs, so latency is bounded by the 15-minute poll cycle. F5Bot adds a parallel path with its own 2–5 minute detection window.

### 3.3 Why Not Webhooks or Streaming?

True real-time (sub-minute) would require a persistent server receiving webhooks, which means hosting costs. The 15-minute polling model keeps the system entirely within GitHub Actions' free tier with no server to maintain. For a brand monitoring use case, 5–30 minute latency is more than sufficient.

If latency requirements tighten in the future, the architecture supports migrating to a lightweight server (e.g., a free-tier Railway or Render deployment) that receives F5Bot webhooks and runs continuous polling loops.

---

## 4. Architecture

### 4.1 System Flow

The system follows a simple pipeline that runs on every scheduled invocation:

1. GitHub Actions triggers the workflow on a 15-minute cron schedule.
2. The orchestrator (`monitor.py`) calls each source adapter in parallel using `asyncio`.
3. Each adapter fetches new items and returns a normalized list of mentions.
4. The deduplicator checks each mention against previously seen items (stored in `seen.json`).
5. New (unseen) mentions are formatted as Slack Block Kit messages and posted to `#niahealth-mentions`.
6. The updated `seen.json` is committed back to the repository to persist state across runs.

### 4.2 Repo Structure

```
niahealth-monitor/
├── monitor.py              # Main orchestrator
├── sources/
│   ├── google_news.py      # Google News RSS adapter
│   ├── google_alerts.py    # Google Alerts RSS adapter
│   ├── reddit.py           # Reddit JSON API adapter
│   ├── hackernews.py       # Algolia HN Search adapter
│   └── newsdata.py         # NewsData.io API adapter
├── slack_poster.py         # Formats + posts Slack Block Kit messages
├── dedup.py                # Manages seen.json, hashing, duplicate checks
├── config.yaml             # Keywords, source URLs, Slack config, settings
├── seen.json               # Dedup state (committed back after each run)
├── .github/workflows/
│   └── monitor.yml         # GitHub Actions cron workflow
├── requirements.txt
└── README.md
```

### 4.3 Deduplication

The same story will often appear across multiple sources. The deduplicator prevents the Slack channel from being flooded with repeats. Each mention is hashed using a normalized version of its title (lowercased, punctuation stripped, whitespace collapsed). The hash is checked against `seen.json` before posting.

Seen entries are stored with a timestamp and automatically pruned after 30 days to prevent the file from growing indefinitely. URLs are also tracked as a secondary dedup key, since different sources sometimes use different headline phrasing for the same article.

---

## 5. Slack Channel Design

The `#niahealth-mentions` channel is designed to be scannable at a glance. Every post follows a consistent format so team members can quickly assess what's happening without opening every link.

### 5.1 Message Format

Each Slack message uses Block Kit and follows this structure:

> 📰 **[Headline as clickable link]**
> *Source Name · Apr 10, 2026 · via Google News*
> First 200 characters of the article description or snippet...

### 5.2 Emoji Legend

| Emoji | Source Type | When Used |
|---|---|---|
| 📰 | News Article | Google News, Google Alerts, NewsData.io results |
| 💬 | Reddit | Reddit posts or comments mentioning NiaHealth |
| 🔶 | Hacker News | HN posts or comments |
| 🔔 | F5Bot Alert | Mentions caught by F5Bot (Reddit, HN, Lobsters) |

### 5.3 Volume Expectations

For a company the size of NiaHealth, expect low volume initially — likely 0–5 mentions per day across all sources. This will grow as the company's public profile increases. The channel should remain highly signal-rich and never feel noisy. If volume exceeds 15–20 mentions per day in the future, that's a good signal to consider the digest and filtering features described in the Future Considerations section.

---

## 6. Configuration

All tunable parameters live in `config.yaml`. No code changes are needed to add keywords, adjust polling intervals, or change Slack channels.

```yaml
keywords:
  - "NiaHealth"
  - "Nia Health"
  - "niahealth.com"
  # Add founder names, product names below

sources:
  google_news:
    enabled: true
    locale: "en-CA"
  google_alerts:
    enabled: true
    feed_urls: []          # Add RSS URLs from Google Alerts setup
  reddit:
    enabled: true
  hackernews:
    enabled: true
  newsdata:
    enabled: true

slack:
  channel: "#niahealth-mentions"

dedup:
  ttl_days: 30
```

### 6.1 Secrets Management

Sensitive values are stored in GitHub Actions Secrets, not in the config file:

- **SLACK_WEBHOOK_URL** — Incoming Webhook URL for the `#niahealth-mentions` channel
- **NEWSDATA_API_KEY** — Free-tier API key from NewsData.io

No other API keys are needed. Google News RSS, Google Alerts RSS, Reddit's JSON endpoint, and the Algolia HN API are all unauthenticated.

---

## 7. GitHub Actions Workflow

The monitor runs as a scheduled GitHub Actions workflow. The workflow file (`.github/workflows/monitor.yml`) defines a cron trigger, installs Python dependencies, runs `monitor.py`, and commits any changes to `seen.json` back to the repo.

### 7.1 Free Tier Budget

GitHub's free plan provides 2,000 minutes per month for private repositories. Usage estimate:

- 96 runs/day × ~45 seconds/run = ~72 minutes/day
- ~2,160 minutes/month (slightly over the 2,000 limit for private repos)

**Recommendation:** Make the repo public for unlimited free minutes, or reduce polling to every 20 minutes (~1,620 min/month) for private repos.

### 7.2 State Persistence

After each run, the workflow commits updated `seen.json` back to the main branch using a GitHub Actions bot commit. The commit message is standardized (e.g., `chore: update seen.json [skip ci]`) and uses the `[skip ci]` tag to prevent the commit from triggering another workflow run.

---

## 8. Dependencies

| Package | Purpose |
|---|---|
| `feedparser` | Parse RSS/Atom feeds from Google News and Google Alerts |
| `httpx` | Async HTTP client for parallel source fetching |
| `slack_sdk` | Official Slack SDK for posting via webhook |
| `pyyaml` | Parse `config.yaml` |

No database is required. State is stored in a JSON file committed to the repository.

---

## 9. Setup Checklist

1. Create the GitHub repository (public recommended for unlimited Actions minutes).
2. Set up a Slack Incoming Webhook and create the `#niahealth-mentions` channel.
3. Register for a free NewsData.io API key.
4. Create Google Alerts for each keyword and select "RSS feed" as delivery.
5. Sign up for F5Bot (free) and add NiaHealth-related keywords.
6. Add `SLACK_WEBHOOK_URL` and `NEWSDATA_API_KEY` to GitHub Actions Secrets.
7. Configure keywords and source settings in `config.yaml`.
8. Push the code and verify the first scheduled run posts to Slack.

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Google News RSS format changes | News source goes silent | Other sources provide redundancy; add health check alerting |
| Reddit rate-limits unauthenticated requests | Reddit mentions delayed or missed | F5Bot acts as backup; can switch to authenticated API if needed |
| NewsData.io changes free tier limits | Reduced API coverage | Google News RSS and Alerts cover the same ground; NewsData is supplementary |
| GitHub Actions scheduling delays | Mentions arrive later than expected | GH Actions cron can be delayed up to 15 min during high load; acceptable for this use case |
| `seen.json` grows too large | Slower git operations | 30-day auto-prune keeps file under a few hundred KB |

---

## 11. Future Considerations (Parked)

The following features are out of scope for Phase 1 but are natural extensions of this system. They are documented here for future planning.

### 11.1 `#competitor-intel` Channel

A second Slack channel dedicated to competitor monitoring. This would use the same source adapters with a separate keyword list for 5–8 key competitors. Posts would be tagged with the competitor name for filtering. The dedup system already supports multiple channels with separate state files.

### 11.2 `#industry-pulse` Channel

A broader channel for Canadian health tech industry news — policy changes, funding trends, regulatory updates, and conference announcements. This channel would require more aggressive keyword filtering to manage volume, potentially including an LLM-based relevance scorer to separate signal from noise.

### 11.3 Weekly Roundup Digest

An automated weekly summary posted every Friday to a `#weekly-roundup` channel (or inline in the existing channels). The digest would include total mention counts by source, the top 3–5 most significant mentions ranked by source authority or engagement, and any notable trends or spikes. This could be generated using a lightweight LLM summarization step at the end of each week.

### 11.4 Sentiment Tagging

Adding positive/negative/neutral sentiment labels to each mention using a lightweight NLP model or LLM API call. This would help the team quickly prioritize responses, especially for negative mentions that need immediate attention.

### 11.5 Additional Platforms

Twitter/X monitoring if API costs become feasible or a reliable free alternative emerges. LinkedIn monitoring if their API opens up for brand mention tracking. Instagram is deprioritized — NiaHealth's B2B health tech audience is unlikely to generate meaningful signal there. Mastodon and Bluesky could be added via their open APIs if the team identifies relevant communities.

### 11.6 Hosted Deployment

If sub-5-minute latency becomes a hard requirement, the system can migrate from GitHub Actions to a lightweight always-on deployment on Railway, Render, or Fly.io free tiers. This would enable webhook-based ingestion from F5Bot and continuous polling loops rather than 15-minute cron intervals.