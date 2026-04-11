"""
Deduplication engine — prevents the same mention from being posted twice.

Primary key: normalized title hash (lowercased, punctuation stripped, whitespace collapsed).
Secondary key: URL hash (catches same article with different headline phrasing).

Entries are stored with timestamps and auto-pruned after a configurable TTL.
"""

import json
import re
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

SEEN_PATH = Path(__file__).parent / "seen.json"


def _normalize_title(title: str) -> str:
    text = title.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def load_seen() -> dict:
    if SEEN_PATH.exists():
        with open(SEEN_PATH) as f:
            return json.load(f)
    return {"titles": {}, "urls": {}}


def save_seen(seen: dict, ttl_days: int = 30):
    cutoff = (
        datetime.now(timezone.utc) - timedelta(days=ttl_days)
    ).isoformat()

    seen["titles"] = {
        k: v for k, v in seen["titles"].items() if v >= cutoff
    }
    seen["urls"] = {
        k: v for k, v in seen["urls"].items() if v >= cutoff
    }

    with open(SEEN_PATH, "w") as f:
        json.dump(seen, f, indent=2)


def is_duplicate(seen: dict, title: str, url: str) -> bool:
    if not title and not url:
        return True
    title_hash = _hash(_normalize_title(title))
    url_hash = _hash(url)
    return title_hash in seen["titles"] or url_hash in seen["urls"]


def mark_seen(seen: dict, title: str, url: str):
    now = datetime.now(timezone.utc).isoformat()
    seen["titles"][_hash(_normalize_title(title))] = now
    seen["urls"][_hash(url)] = now
