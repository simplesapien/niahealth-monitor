"""Google News RSS adapter — highest-value free source for news coverage."""

import feedparser
import httpx

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NiaHealth-Monitor/1.0)"}


async def fetch(
    client: httpx.AsyncClient,
    keywords: list[str],
    source_config: dict,
) -> list[dict]:
    locale = source_config.get("locale", "en-CA")
    parts = locale.split("-")
    country = parts[1] if len(parts) > 1 else "CA"

    mentions: list[dict] = []

    for keyword in keywords:
        params = {
            "q": keyword,
            "hl": locale,
            "gl": country,
            "ceid": f"{country}:{locale}",
        }
        try:
            resp = await client.get(
                "https://news.google.com/rss/search",
                params=params,
                headers=_HEADERS,
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] Google News '{keyword}': {e}")
            continue

        feed = feedparser.parse(resp.text)
        for entry in feed.entries:
            source = entry.get("source")
            if source and hasattr(source, "title"):
                source_name = source.title
            elif isinstance(source, dict):
                source_name = source.get("title", "Google News")
            else:
                source_name = "Google News"

            mentions.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "source_name": source_name,
                "source_type": "google_news",
                "published": entry.get("published", ""),
                "snippet": entry.get("summary", "")[:200],
            })

    return mentions
