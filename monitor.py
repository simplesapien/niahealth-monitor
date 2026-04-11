#!/usr/bin/env python3
"""
NiaHealth Mentions Monitor — searches free public sources for brand mentions
and posts formatted alerts to the #niahealth-mentions Slack channel.

Sources are fetched in parallel via asyncio + httpx, deduplicated against
seen.json, and posted to Slack via the official SDK.
"""

import asyncio
import os
import time
from pathlib import Path

import httpx
import yaml
from slack_sdk.webhook import WebhookClient

import dedup
import slack_poster
from sources import ADAPTERS

SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR / "config.yaml"


async def fetch_all_mentions(
    keywords: list[str], sources_config: dict
) -> list[dict]:
    """Call every enabled source adapter in parallel, return combined results."""
    newsdata_key = os.environ.get("NEWSDATA_API_KEY", "")

    async with httpx.AsyncClient() as client:
        tasks = []
        task_names = []

        for name, fetch_fn in ADAPTERS.items():
            src_conf = sources_config.get(name, {})
            if not src_conf.get("enabled", True):
                print(f"  {name}: disabled")
                continue
            if name == "newsdata":
                src_conf = {**src_conf, "api_key": newsdata_key}
            tasks.append(fetch_fn(client, keywords, src_conf))
            task_names.append(name)

        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_mentions: list[dict] = []
    for name, result in zip(task_names, results):
        if isinstance(result, Exception):
            print(f"  [error] {name}: {result}")
            continue
        print(f"  {name}: {len(result)} items fetched")
        all_mentions.extend(result)

    return all_mentions


def main():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    seen = dedup.load_seen()
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

    if not webhook_url and not dry_run:
        raise SystemExit(
            "SLACK_WEBHOOK_URL is required (or set DRY_RUN=1)"
        )

    keywords = config["keywords"]
    sources_config = config.get("sources", {})
    ttl_days = config.get("dedup", {}).get("ttl_days", 30)

    print(f"Keywords: {keywords}")
    print("Fetching sources...")
    all_mentions = asyncio.run(
        fetch_all_mentions(keywords, sources_config)
    )
    print(f"Total items fetched: {len(all_mentions)}")

    cap = config.get("max_posts_per_run", 15)
    new_mentions = [
        m
        for m in all_mentions
        if m.get("title") and m.get("url")
        and not dedup.is_duplicate(seen, m["title"], m["url"])
    ]
    print(f"New mentions: {len(new_mentions)} (cap: {cap})")

    if new_mentions:
        wh_client = WebhookClient(url=webhook_url) if webhook_url else None
        for mention in new_mentions[:cap]:
            dedup.mark_seen(seen, mention["title"], mention["url"])
            slack_poster.post(wh_client, mention)
            if not dry_run:
                time.sleep(1)

    dedup.save_seen(seen, ttl_days=ttl_days)
    print("Done.")


if __name__ == "__main__":
    main()
