#!/usr/bin/env python3
"""
Return the next active HubSpot ownerId in round-robin order.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
from typing import Any, Dict, List


def _load_last(path: pathlib.Path) -> int | None:
    try:
        return int(path.read_text())
    except Exception:  # noqa: BLE001
        return None


def _save_last(path: pathlib.Path, owner_id: int) -> None:
    path.write_text(str(owner_id))


def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get the next active ownerId in round-robin rotation."""
    try:
        # Import dependencies inside the function to avoid top-level import issues
        from hubspot_hub_helpers import OWNER_STATE_PATH, hs_client
        
        path = pathlib.Path(OWNER_STATE_PATH)

        # Fix: Check for active attribute existence and handle different owner object types
        owners = []
        for o in hs_client().crm.owners.owners_api.get_page().results:
            try:
                # Check if owner has active attribute and is active
                is_active = getattr(o, 'active', True)  # Default to True if no active attribute
                owner_type = getattr(o, 'type_', getattr(o, 'type', 'PERSON'))  # Handle different attribute names
                
                if is_active and owner_type == "PERSON":
                    owners.append(o.id)
            except Exception:
                # Skip owners that cause issues, but don't fail the whole operation
                continue
        
        if not owners:
            return {"error": "No active owners found in HubSpot"}

        last = _load_last(path)
        next_owner = owners[(owners.index(last) + 1) % len(owners)] if last in owners else owners[0]
        _save_last(path, next_owner)

        return {
            "status": "success",
            "ownerId": next_owner,
            "totalActiveOwners": len(owners)
        }
    
    except Exception as e:
        return {"error": f"Failed to get next owner: {str(e)}"}


def main() -> None:
    # Test mode for autodiscovery (REQUIRED)
    if len(sys.argv) == 2 and sys.argv[1] == '{"__test__": true}':
        print(json.dumps({"success": True, "_simple": True}))
        return
    
    # Optional: Rich schema for better LLM integration
    if len(sys.argv) == 2 and sys.argv[1] == "--fractalic-dump-schema":
        schema = {
            "description": "Get the next active HubSpot ownerId in round-robin order. Maintains state between calls to ensure fair distribution of ownership assignments.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
        print(json.dumps(schema, ensure_ascii=False))
        return
    
    # Process JSON input (REQUIRED)
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected exactly one JSON argument")
        
        params = json.loads(sys.argv[1])
        result = process_data(params)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
