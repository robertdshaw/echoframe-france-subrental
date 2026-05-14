"""
NewsData.io client — French-language news headlines.

Endpoint: https://newsdata.io/api/1/news
Auth: NEWSDATA_API_KEY (free tier: 200 req/day, 10 results/req).

We filter on `country=fr` + `language=fr` and let the relevance
filter in nlp/relevance_filter.py drop off-topic items downstream.
Falls back to the seed corpus when no key is set.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx

from config import settings
from data.property_seeder import load_news_signals


logger = logging.getLogger(__name__)


class NewsDataClient:
    BASE_URL = "https://newsdata.io/api/1/news"
    TIMEOUT = 12.0

    def __init__(self) -> None:
        self.api_key = settings.newsdata_api_key

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def get_french_news(self, limit: int = 50, query: str | None = None) -> List[Dict[str, Any]]:
        """Most recent French-language news, optionally narrowed by query."""
        if not self.is_configured:
            return load_news_signals()[:limit]
        try:
            params: Dict[str, Any] = {
                "apikey": self.api_key,
                "country": "fr",
                "language": "fr",
                "size": min(10, limit),  # free tier caps at 10 per request
            }
            if query:
                params["q"] = query
            async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                r = await client.get(self.BASE_URL, params=params)
                r.raise_for_status()
                payload = r.json()
                results = payload.get("results", []) or []
                return [
                    {
                        "id": item.get("article_id"),
                        "headline": item.get("title"),
                        "source": item.get("source_name") or item.get("source_id"),
                        "date": item.get("pubDate", "")[:10],
                        "keywords": item.get("keywords") or [],
                        "category": (item.get("category") or ["other"])[0],
                        "url": item.get("link"),
                        "fetched_at": datetime.utcnow().isoformat(),
                    }
                    for item in results
                ]
        except Exception as exc:
            logger.warning("NewsData.io fetch failed (%s); using seed", exc)
            return load_news_signals()[:limit]


newsdata_client = NewsDataClient()
