"""
Slack Block Kit formatter and poster.

Each mention is posted as a clean, scannable card with:
- Source icon + bold clickable headline
- Metadata line (subreddit, date, source)
- Snippet preview
"""

import os
import re

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


def _clean_snippet(raw: str, limit: int = 180) -> str:
    text = re.sub(r"<[^>]+>", "", raw)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def post(webhook_client: WebhookClient | None, mention: dict):
    emoji = EMOJI.get(mention["source_type"], "📰")
    via = VIA_LABEL.get(mention["source_type"], mention["source_type"])
    source_name = mention.get("source_name", via)
    published = mention.get("published", "")
    title = mention["title"]
    url = mention["url"]
    snippet = _clean_snippet(mention.get("snippet", ""))

    meta_parts = [p for p in [source_name, published] if p]
    meta = " · ".join(meta_parts)

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji}  *<{url}|{title}>*",
            },
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": meta},
            ],
        },
    ]

    if snippet:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f">{snippet}",
            },
        })

    blocks.append({"type": "divider"})

    fallback = f"{emoji} {title} — {source_name}"

    if DRY_RUN:
        print(f"  [dry-run] {fallback}")
        return

    if not webhook_client:
        return

    resp = webhook_client.send(text=fallback, blocks=blocks)
    if resp.status_code != 200:
        print(f"  [warn] Slack post failed ({resp.status_code}): {resp.body}")
