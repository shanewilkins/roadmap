#!/usr/bin/env python3
"""Make common naive datetime calls timezone-aware across the workspace.

This script performs conservative replacements:
- Replaces `datetime.now(timezone.utc)` -> `datetime.now(timezone.utc)`
- Replaces `datetime.now(timezone.utc)` -> `datetime.now(timezone.utc)` (only exact empty-arg calls)
- Ensures `timezone` is imported when `from datetime import datetime, timezone` is used.

It skips the .roadmap archive folder, virtualenvs, and non-.py files.

Run locally and inspect changes before committing.
"""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", "venv", "htmlcov", ".git", ".roadmap"}

py_files = []
for dirpath, _dirnames, filenames in os.walk(ROOT):
    # skip excluded directories
    parts = Path(dirpath).parts
    if any(p in EXCLUDE_DIRS for p in parts):
        continue
    for f in filenames:
        if not f.endswith(".py"):
            continue
        py_files.append(Path(dirpath) / f)

re_utcnow = re.compile(r"datetime\.utcnow\(\)")
re_now_empty = re.compile(r"datetime\.now\(\)")
re_from_datetime_import = re.compile(r"from\s+datetime\s+import\s+(.*)\bdatetime\b(.*)")

modified_files = []
for path in py_files:
    text = path.read_text(encoding="utf-8")
    new_text = text
    changed = False

    if "datetime.now(timezone.utc)" in new_text:
        new_text = re_utcnow.sub("datetime.now(timezone.utc)", new_text)
        changed = True

    if "datetime.now(timezone.utc)" in new_text:
        new_text = re_now_empty.sub("datetime.now(timezone.utc)", new_text)
        changed = True

    if changed:
        # Ensure timezone is imported when "from datetime import datetime" is used
        if "from datetime import" in new_text:
            # If 'timezone' already imported, skip
            if "timezone" not in new_text.splitlines()[0:20]:
                # Try to find a from-import that includes datetime
                def add_timezone_to_from_import(text):
                    for m in re_from_datetime_import.finditer(text):
                        full = m.group(0)
                        # if timezone already in that import, skip
                        if "timezone" in full:
                            return text
                        # replace the import line by inserting timezone
                        new_full = full.replace("datetime", "datetime, timezone")
                        return text.replace(full, new_full, 1)
                    return text

                new_text = add_timezone_to_from_import(new_text)
        # If file uses 'import datetime' style, no change to imports required

    if changed and new_text != text:
        path.write_text(new_text, encoding="utf-8")
        modified_files.append(str(path.relative_to(ROOT)))

if modified_files:
    print("Modified files:")
    for f in modified_files:
        print(f)
else:
    print("No files modified.")
