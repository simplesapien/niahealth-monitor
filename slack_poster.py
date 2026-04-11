"""
Slack Block Kit formatter and poster.

Each mention is posted with a source-specific emoji, a clickable headline,
metadata line (source · date · via), and a snippet.
"""

import os

from slack_sdk.webhook import WebhookClient

EMOJI = {
    "google_news": "📰",
    "google_alerts": "📰",
    "newsdata": "📰",
    "reddit": "💬",
    "hackernews": "🔶",
    "f5bot": "🔔",
}

VIA_LABEL = {
    "google_news": "Google News",
    "google_alerts": "Google Alerts",
    "newsdata": "NewsData.io",
    "reddit": "Reddit",
    "hackernews": "Hacker News",
    "f5bot": "F5Bot",
}

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")


def post(webhook_client: WebhookClient | None, mention: dict):
    emoji = EMOJI.get(mention["source_type"], "📰")
    via = VIA_LABEL.get(mention["source_type"], mention["source_type"])
    source_name = mention.get("source_name", via)
    published = mention.get("published", "")
    title = mention["title"]
    url = mention["url"]
    snippet = mention.get("snippet", "")[:200]

    meta_parts = [p for p in [source_name, published, f"via {via}"] if p]
    meta = " · ".join(meta_parts)

    text = f"{emoji} *<{url}|{title}>*\n_{meta}_"
    if snippet:
        text += f"\n{snippet}"

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {"type": "divider"},
    ]
    fallback = f"{emoji} {title}"

    if DRY_RUN:
        print(f"  [dry-run] {fallback}")
        return

    if not webhook_client:
        return

    resp = webhook_client.send(text=fallback, blocks=blocks)
    if resp.status_code != 200:
        print(f"  [warn] Slack post failed ({resp.status_code}): {resp.body}")
