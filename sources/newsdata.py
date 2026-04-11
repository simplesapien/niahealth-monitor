"""NewsData.io adapter — supplements Google News with broader international coverage."""

import httpx


async def fetch(
    client: httpx.AsyncClient,
    keywords: list[str],
    source_config: dict,
) -> list[dict]:
    api_key = source_config.get("api_key", "")
    if not api_key:
        print("  [skip] NewsData.io: no API key configured")
        return []

    mentions: list[dict] = []

    for keyword in keywords:
        params = {"apikey": api_key, "q": keyword, "language": "en"}
        try:
            resp = await client.get(
                "https://newsdata.io/api/1/news",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] NewsData.io '{keyword}': {e}")
            continue

        data = resp.json()
        for article in data.get("results", []):
            mentions.append({
                "title": article.get("title", ""),
                "url": article.get("link", ""),
                "source_name": article.get("source_id", "NewsData.io"),
                "source_type": "newsdata",
                "published": article.get("pubDate", ""),
                "snippet": (article.get("description") or "")[:200],
            })

    return mentions
