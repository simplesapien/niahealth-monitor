"""Hacker News adapter — uses the free Algolia HN Search API."""

import httpx


def _matches(text: str, keyword: str) -> bool:
    """Post-filter: ensure the keyword actually appears in the text."""
    return keyword.strip('"').lower() in text.lower()


async def fetch(
    client: httpx.AsyncClient,
    keywords: list[str],
    source_config: dict,
) -> list[dict]:
    mentions: list[dict] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        params = {"query": keyword, "tags": "(story,comment)"}
        try:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search_by_date",
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] Hacker News '{keyword}': {e}")
            continue

        data = resp.json()
        for hit in data.get("hits", []):
            obj_id = hit.get("objectID", "")
            if obj_id in seen_ids:
                continue

            is_comment = bool(hit.get("comment_text"))

            if is_comment:
                title = hit.get("story_title", "") or "HN Comment"
                searchable = title + " " + hit.get("comment_text", "")
                item_url = (
                    f"https://news.ycombinator.com/item?id={obj_id}"
                )
                snippet = hit["comment_text"][:200]
            else:
                title = hit.get("title", "")
                searchable = title
                item_url = hit.get("url") or (
                    f"https://news.ycombinator.com/item?id={obj_id}"
                )
                snippet = ""

            if not _matches(searchable, keyword):
                continue
            seen_ids.add(obj_id)

            created = hit.get("created_at", "")

            mentions.append({
                "title": title,
                "url": item_url,
                "source_name": "Hacker News",
                "source_type": "hackernews",
                "published": created[:10] if created else "",
                "snippet": snippet,
            })

    return mentions
