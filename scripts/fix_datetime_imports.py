#!/usr/bin/env python3
"""Fix incorrectly rewritten datetime import lines produced by the earlier script.

Replaces leading 'from datetime import ' with 'from datetime import '.
Also handles a few malformed splits where comma placement is wrong.
"""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".venv", "venv", "htmlcov", ".git"}

count = 0
for dirpath, _dirnames, filenames in os.walk(ROOT):
    parts = Path(dirpath).parts
    if any(p in EXCLUDE_DIRS for p in parts):
        continue
    if ".roadmap" in parts:
        continue
    for f in filenames:
        if not f.endswith(".py"):
            continue
        p = Path(dirpath) / f
        text = p.read_text(encoding="utf-8")
        if "from datetime import" in text:
            new = text.replace("from datetime import", "from datetime import")
            # Also fix odd split like 'from datetime import datetime, timezon\ne'
            new = new.replace("from datetime import", "from datetime import")
            if new != text:
                p.write_text(new, encoding="utf-8")
                print("Fixed", p.relative_to(ROOT))
                count += 1
print("Fixed files:", count)
