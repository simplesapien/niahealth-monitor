from sources import google_news, google_alerts, reddit, hackernews, newsdata

ADAPTERS = {
    "google_news": google_news.fetch,
    "google_alerts": google_alerts.fetch,
    "reddit": reddit.fetch,
    "hackernews": hackernews.fetch,
    "newsdata": newsdata.fetch,
}
