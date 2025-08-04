#!/usr/bin/env python3
"""
Shared helpers for all HubSpot tools.

• Implements the Simple-JSON autodiscovery handshake.
• Provides hs_client(), ok(), fatal(), and auto_probe().
• Central Brain is stubbed to stderr for now.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from functools import lru_cache
from typing import Any, Dict, List

import requests
from hubspot import HubSpot

# ------------------------------------------------------------------------------
# Configuration (override via environment variables)
# ------------------------------------------------------------------------------
TOOL: str = os.path.splitext(os.path.basename(sys.argv[0]))[0]
HUBSPOT_TOKEN: str | None = os.getenv("HUBSPOT_TOKEN")
CENTRAL_BRAIN_URL: str | None = os.getenv("CENTRAL_BRAIN_URL")  # optional
OWNER_STATE_PATH: str = os.getenv("HS_OWNER_STATE", "/tmp/hs_owner_rr.state")
HTTP_TIMEOUT: int = int(os.getenv("HS_HTTP_TIMEOUT", "10"))

# ------------------------------------------------------------------------------
# Logging (stderr only; stdout must remain pure JSON for Fractalic)
# ------------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(TOOL)


# ------------------------------------------------------------------------------
# Autodiscovery helpers
# ------------------------------------------------------------------------------
def auto_probe(argv: List[str], dump_schema_fn) -> bool:
    """Handle autodiscovery probe requests quickly."""
    if len(argv) == 2:
        if argv[1] == '{"__test__": true}':
            print(json.dumps({"success": True, "_simple": True}))
            return True
        elif argv[1] == "--fractalic-dump-schema":
            dump_schema_fn()
            return True
    return False


# ------------------------------------------------------------------------------
# Central Brain (stub: print to stderr or POST if URL is set)
# ------------------------------------------------------------------------------
def _brain(payload: Dict[str, Any]) -> None:
    if CENTRAL_BRAIN_URL:
        try:
            requests.post(CENTRAL_BRAIN_URL, json=payload, timeout=3)
        except Exception:  # noqa: BLE001 – reporting must not kill main flow
            log.debug("Central Brain unreachable.")
    else:
        log.warning("[CentralBrain] %s", json.dumps(payload, ensure_ascii=False))


# ------------------------------------------------------------------------------
# HubSpot client (singleton)
# ------------------------------------------------------------------------------
@lru_cache(maxsize=1)
def hs_client() -> HubSpot:
    if not HUBSPOT_TOKEN:
        fatal("ENV_MISSING_TOKEN", "HUBSPOT_TOKEN environment variable is not set")
    try:
        return HubSpot(access_token=HUBSPOT_TOKEN)
    except Exception as err:
        fatal("HS_AUTH_FAILED", f"HubSpot authentication failed: {err}")


# ------------------------------------------------------------------------------
# Consistent structured results
# ------------------------------------------------------------------------------
def ok(
    operation: str,
    data: Dict[str, Any] | None,
    *,
    start: float,
) -> None:
    result = {
        "status": "ok",
        "tool": TOOL,
        "elapsed_ms": int((time.time() - start) * 1000),
        "operation": operation,
        "data": data or {},
    }
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0)


def fatal(
    code: str,
    message: str,
    *,
    start: float | None = None,
    context: Dict[str, Any] | None = None,
) -> None:
    result = {
        "status": "error",
        "tool": TOOL,
        "elapsed_ms": int((time.time() - start) * 1000) if start else 0,
        "code": code,
        "message": message,
        "context": context or {},
    }
    _brain(result)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(1)
