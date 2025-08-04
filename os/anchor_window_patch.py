#!/usr/bin/env python3
"""
name: anchor_window_patch
description: |
  Replace an exact snippet in a text file using only surrounding *anchor lines*.
  The tool searches for the unique sequence:

      <anchor_before> … <old_snippet> … <anchor_after>

  inside a sliding window (default 2 000 characters) and swaps *old_snippet*
  with *new_snippet*.  A unified diff of the change is printed to **stdout**;
  errors go to **stderr** (so Fractalic can decide what to do).

parameters:
  type: object
  properties:
    path:
      type: string
      description: |
        File to patch.  Relative paths are interpreted from the current working
        directory of the Fractalic run.
    anchor_before:
      type: string
      description: |
        Text that must appear **immediately before** the snippet block.
        Can span multiple lines.  Required.
    old_snippet:
      type: string
      description: |
        Exact text to be replaced.  Required.
    new_snippet:
      type: string
      description: |
        Replacement text.  Required.
    anchor_after:
      type: string
      description: |
        Text that must appear **after** the snippet block.  Can span multiple
        lines.  Required.
    window:
      type: integer
      description: |
        How many characters *after* `anchor_before` to search for
        `old_snippet` (increase for huge files).  Optional, default 2000.
  required: [path, anchor_before, old_snippet, new_snippet, anchor_after]
examples:
  - |
    {
      "path": "src/hello.js",
      "anchor_before": "function greet() {",
      "old_snippet": "console.log(\\"Hello Wordl!\\");",
      "new_snippet": "console.log(\\"Hello World!\\");",
      "anchor_after": "}",
      "window": 500
    }
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from typing import Tuple

# Optional dependency: try to import patch-ng (maintained fork of python-patch)
try:
    import patch_ng as patchlib
except ModuleNotFoundError:
    patchlib = None


# --------------------------------------------------------------------------- #
# Core helpers
# --------------------------------------------------------------------------- #
def find_region(
    text: str,
    anchor_before: str,
    old: str,
    anchor_after: str,
    window: int,
) -> Tuple[int, int]:
    """Return byte-offset (start, end) of *old* inside *text*."""
    cursor = 0
    matches: list[Tuple[int, int]] = []

    while True:
        idx_before = text.find(anchor_before, cursor)
        if idx_before == -1:
            break

        search_start = idx_before + len(anchor_before)
        search_end = search_start + window
        segment = text[search_start:search_end]

        idx_old = segment.find(old)
        if idx_old != -1:
            idx_old_abs = search_start + idx_old
            idx_after_abs = text.find(anchor_after, idx_old_abs + len(old))
            if idx_after_abs != -1:
                matches.append((idx_old_abs, idx_old_abs + len(old)))

        cursor = idx_before + 1

    if not matches:
        raise ValueError("Pattern not found.  Try enlarging 'window' or refining anchors.")
    if len(matches) > 1:
        raise ValueError("Pattern ambiguous.  Anchors match multiple locations.")
    return matches[0]


def unified_diff(original: str, updated: str, path: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        )
    )


def patch_file(
    *,
    path: str,
    anchor_before: str,
    old_snippet: str,
    new_snippet: str,
    anchor_after: str,
    window: int,
) -> str:
    with open(path, encoding="utf-8") as fh:
        original = fh.read()

    start, end = find_region(original, anchor_before, old_snippet, anchor_after, window)
    updated = original[:start] + new_snippet + original[end:]

    if original == updated:
        raise ValueError("No change detected (old_snippet already equals new_snippet).")

    diff_text = unified_diff(original, updated, path)

    # Write file back to disk
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(updated)

    # If patch-ng is available, verify we produced a valid diff
    if patchlib:
        if not patchlib.fromstring(diff_text).apply():
            raise RuntimeError("Patch verification failed after writing file.")

    return diff_text


# --------------------------------------------------------------------------- #
# CLI entry-point (supports either JSON spec or individual flags)
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    # Create a basic parser that has all the core arguments
    # This ensures basic help and introspection works correctly
    p = argparse.ArgumentParser(
        prog="anchor_window_patch",
        description="Replace an exact snippet in a text file using only surrounding anchor lines.",
    )

    # Add all arguments directly to make introspection easier
    p.add_argument(
        "--path", 
        help="File to patch. Relative to current working directory."
    )
    p.add_argument(
        "--anchor-before",
        dest="anchor_before",
        help="Text immediately before the snippet to replace."
    )
    p.add_argument(
        "--old-snippet",
        dest="old_snippet",
        help="Exact text to be replaced."
    )
    p.add_argument(
        "--new-snippet",
        dest="new_snippet",
        help="Replacement text."
    )
    p.add_argument(
        "--anchor-after",
        dest="anchor_after",
        help="Text immediately after the snippet to replace."
    )
    p.add_argument(
        "--window",
        type=int,
        default=2000,
        help="How many characters after anchor_before to search for old_snippet. Default: 2000."
    )
    
    # Also add spec options but make them mutually exclusive with path
    group = p.add_argument_group("Alternative specification")
    spec_group = group.add_mutually_exclusive_group()
    spec_group.add_argument(
        "--spec",
        help="JSON string with all parameters (alternative to individual flags)."
    )
    spec_group.add_argument(
        "--spec-file",
        help="Path to a JSON file with all parameters."
    )
    
    # Add the Fractalic schema dump flag
    p.add_argument("--fractalic-dump-schema", action="store_true", help=argparse.SUPPRESS)
    
    ns = p.parse_args()

    # Build params dict
    if ns.spec or ns.spec_file:
        spec_src = (
            open(ns.spec_file, encoding="utf-8").read() if ns.spec_file else ns.spec
        )
        try:
            params = json.loads(spec_src)
        except json.JSONDecodeError as e:
            p.error(f"--spec JSON invalid: {e}")
    else:
        params = {
            k: getattr(ns, k)
            for k in (
                "path",
                "anchor_before",
                "old_snippet",
                "new_snippet",
                "anchor_after",
                "window",
            )
            if getattr(ns, k) is not None
        }

    # Check mandatory fields
    missing = [k for k in ("path", "anchor_before", "old_snippet", "new_snippet", "anchor_after") if k not in params]
    if missing:
        p.error(f"Missing required parameter(s): {', '.join(missing)}")

    return argparse.Namespace(params=params)


def get_tool_schema():
    return {
        "name": "anchor_window_patch",
        "description": "Replace an exact snippet in a text file using only surrounding anchor lines.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File to patch."},
                "anchor_before": {"type": "string", "description": "Text immediately before the snippet."},
                "old_snippet": {"type": "string", "description": "Exact text to be replaced."},
                "new_snippet": {"type": "string", "description": "Replacement text."},
                "anchor_after": {"type": "string", "description": "Text immediately after the snippet."},
                "window": {"type": "integer", "description": "How many characters after anchor_before to search for old_snippet.", "default": 2000}
            },
            "required": ["path", "anchor_before", "old_snippet", "new_snippet", "anchor_after"]
        }
    }


def main() -> None:
    if "--fractalic-dump-schema" in sys.argv:
        import json; print(json.dumps(get_tool_schema(), indent=2)); sys.exit(0)
    try:
        args = parse_args()
        diff = patch_file(**args.params)
        print(diff)  # unified diff -> stdout
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
