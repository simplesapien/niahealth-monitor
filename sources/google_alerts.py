"""Google Alerts RSS adapter — catches long-tail sources Google News may miss."""

import feedparser
import httpx

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NiaHealth-Monitor/1.0)"}


async def fetch(
    client: httpx.AsyncClient,
    keywords: list[str],
    source_config: dict,
) -> list[dict]:
    feed_urls = source_config.get("feed_urls", [])
    if not feed_urls:
        return []

    mentions: list[dict] = []

    for url in feed_urls:
        try:
            resp = await client.get(url, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] Google Alerts feed: {e}")
            continue

        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            mentions.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "source_name": "Google Alerts",
                "source_type": "google_alerts",
                "published": entry.get("published", ""),
                "snippet": entry.get("summary", "")[:200],
            })

    return mentions
