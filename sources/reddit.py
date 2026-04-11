"""Reddit RSS adapter — searches Reddit via public RSS feeds (no auth required).

Makes a single RSS request combining all keywords (brand + extra) into one OR
query to avoid rate limiting. Results are post-filtered to ensure at least one
keyword actually appears in the title or body.
"""

import re

import feedparser
import httpx

_HEADERS = {"User-Agent": "NiaHealth-Monitor/1.0 (social media monitor)"}


def _matches_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw.strip('"').lower() in lower for kw in keywords)


def _build_query(keywords: list[str]) -> str:
    return " OR ".join(f'"{kw.strip(chr(34))}"' for kw in keywords)


async def fetch(
    client: httpx.AsyncClient,
    keywords: list[str],
    source_config: dict,
) -> list[dict]:
    all_keywords = list(keywords) + source_config.get("extra_queries", [])
    query = _build_query(all_keywords)
    params = {"q": query, "sort": "new", "t": "week"}

    try:
        resp = await client.get(
            "https://www.reddit.com/search.rss",
            params=params,
            headers=_HEADERS,
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code == 429:
            print("  [warn] Reddit rate limit, skipping")
            return []
        resp.raise_for_status()
    except Exception as e:
        print(f"  [warn] Reddit: {e}")
        return []

    feed = feedparser.parse(resp.text)
    mentions: list[dict] = []
    seen_urls: set[str] = set()

    for entry in feed.entries:
        url = entry.get("link", "")
        if not url or url in seen_urls:
            continue
        if "/r/" not in url or "/comments/" not in url:
            continue

        title = entry.get("title", "")
        content = entry.get("summary", "")
        searchable = title + " " + content

        if not _matches_any(searchable, all_keywords):
            continue
        seen_urls.add(url)

        published = entry.get("published", "") or entry.get("updated", "")
        author = entry.get("author", "")

        subreddit = ""
        parts = url.split("/")
        if "r" in parts:
            r_idx = parts.index("r")
            if r_idx + 1 < len(parts):
                subreddit = parts[r_idx + 1]

        snippet = re.sub(r"<[^>]+>", "", content)[:200] if content else ""

        mentions.append({
            "title": title,
            "url": url,
            "source_name": f"r/{subreddit}" if subreddit else f"u/{author}" if author else "Reddit",
            "source_type": "reddit",
            "published": published,
            "snippet": snippet,
        })

    return mentions
