"""
Apify client — generic wrapper for running actors synchronously.

Apify exposes a "run-sync-get-dataset-items" endpoint which is exactly
what we want: POST the actor input, wait for it to finish, get the
dataset back in the same request. No polling, no webhooks.

Endpoint:
  POST https://api.apify.com/v2/acts/{actorId}/run-sync-get-dataset-items
  Header: Authorization: Bearer <APIFY_TOKEN>
  Body: actor-specific input JSON
  Response: JSON array of dataset items

Run timeout default: 60s (cold-start of an Apify container is usually
5–15s, scraping a single Airbnb location ~20–40s for ~25 listings).

Auth: APIFY_TOKEN env var. Self-serve at
https://console.apify.com/account/integrations.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx


logger = logging.getLogger(__name__)


class ApifyClient:
    BASE_URL = "https://api.apify.com/v2/"
    # Default run timeout — Apify cold-starts a container per call, so
    # short scrapes still need ~30–60s.
    TIMEOUT = 90.0

    def __init__(self) -> None:
        self.token = os.environ.get("APIFY_TOKEN")

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    async def run_actor_sync(
        self,
        actor_id: str,
        actor_input: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Run an actor and return its dataset items in a single call.

        Apify's actor IDs use `/` in the URL — `tri_angle/new-fast-airbnb-scraper`
        becomes `tri_angle~new-fast-airbnb-scraper` in the path (Apify
        substitutes `~` for `/` per their REST convention).
        """
        result = await self.run_actor_sync_debug(actor_id, actor_input, timeout)
        if result.get("ok"):
            return result.get("data")
        return None

    async def run_actor_sync_debug(
        self,
        actor_id: str,
        actor_input: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Same call as run_actor_sync but returns the full diagnostic shape.

        Returns:
          {
            "ok": bool,
            "http_status": int | None,
            "data": list | None,
            "error": str | None,
            "error_body_excerpt": str | None,
            "actor_id": str,
            "token_present": bool,
          }

        Used by the /api/data-sources/airbnb-diagnose endpoint so we can
        see exactly why Apify is rejecting calls without grepping Render
        logs.
        """
        if not self.is_configured:
            return {
                "ok": False,
                "http_status": None,
                "data": None,
                "error": "APIFY_TOKEN not set",
                "error_body_excerpt": None,
                "actor_id": actor_id,
                "token_present": False,
            }
        path_id = actor_id.replace("/", "~")
        url = f"{self.BASE_URL}acts/{path_id}/run-sync-get-dataset-items"
        try:
            async with httpx.AsyncClient(timeout=timeout or self.TIMEOUT) as client:
                r = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    },
                    json=actor_input,
                )
                if r.status_code >= 400:
                    logger.warning(
                        "Apify %s HTTP %s: %s",
                        actor_id,
                        r.status_code,
                        r.text[:200],
                    )
                    return {
                        "ok": False,
                        "http_status": r.status_code,
                        "data": None,
                        "error": f"HTTP {r.status_code}",
                        "error_body_excerpt": r.text[:500],
                        "actor_id": actor_id,
                        "token_present": True,
                    }
                data = r.json()
                if not isinstance(data, list):
                    logger.warning("Apify %s returned non-list payload", actor_id)
                    return {
                        "ok": False,
                        "http_status": r.status_code,
                        "data": None,
                        "error": "Non-list response payload",
                        "error_body_excerpt": str(data)[:500],
                        "actor_id": actor_id,
                        "token_present": True,
                    }
                return {
                    "ok": True,
                    "http_status": r.status_code,
                    "data": data,
                    "error": None,
                    "error_body_excerpt": None,
                    "actor_id": actor_id,
                    "token_present": True,
                }
        except Exception as exc:
            logger.warning("Apify %s failed: %s", actor_id, exc)
            return {
                "ok": False,
                "http_status": None,
                "data": None,
                "error": f"{type(exc).__name__}: {exc}",
                "error_body_excerpt": None,
                "actor_id": actor_id,
                "token_present": True,
            }


apify_client = ApifyClient()
