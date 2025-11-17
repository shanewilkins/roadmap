#!/usr/bin/env python3
import glob
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
monolith = ROOT / "roadmap" / "cli_backup_original.py"
mod_dir = ROOT / "roadmap" / "cli"

pattern_def = re.compile(r"def\s+(\w+)\s*\(")


def parse_file(path):
    txt = path.read_text()
    lines = txt.splitlines()
    results = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # find decorator blocks
        if line.startswith("@") and (".command" in line or "click.command" in line):
            decs = []
            # collect decorator lines until function def
            while i < len(lines) and lines[i].strip().startswith("@"):
                decs.append(lines[i].strip())
                i += 1
            # after decorators, expect def
            # skip blank/comment lines
            while i < len(lines) and lines[i].strip() == "":
                i += 1
            if i < len(lines) and "def " in lines[i]:
                m = pattern_def.search(lines[i])
                func = m.group(1) if m else "<unknown>"
            else:
                func = "<unknown>"
            results.append(
                {"file": str(path.relative_to(ROOT)), "decorators": decs, "func": func}
            )
        else:
            i += 1
    return results


monolith_cmds = parse_file(monolith)
modular_files = sorted([Path(p) for p in glob.glob(str(mod_dir / "*.py"))])
modular_cmds = []
for f in modular_files:
    modular_cmds.extend(parse_file(f))

# Extract canonical names: prefer explicit name in decorator, else function name
import re


def canonical_name(entry):
    for d in entry["decorators"]:
        m = re.search(r"\.command\s*\(\s*['\"]([^'\"]+)['\"]", d)
        if m:
            return m.group(1)
    # fallback to decorator like @click.command or @group.command without name
    for d in entry["decorators"]:
        m = re.search(r"@([\w_\.]+)\.command", d)
        if m:
            # return group name dot command as best-effort
            return m.group(1) + ".command"
    return entry.get("func")


mono_names = sorted({canonical_name(e) for e in monolith_cmds})
mod_names = sorted({canonical_name(e) for e in modular_cmds})

# Also introspect live Click group if importable
import importlib
import sys

sys.path.insert(0, str(ROOT))

live_names = []
try:
    main = importlib.import_module("roadmap.cli").main
    if hasattr(main, "commands"):
        live_names = sorted(main.commands.keys())
except Exception:
    live_names = []

report = {
    "monolith_count": len(mono_names),
    "modular_count": len(mod_names),
    "monolith_only": sorted(set(mono_names) - set(mod_names)),
    "modular_only": sorted(set(mod_names) - set(mono_names)),
    "live_commands": live_names,
}

import json

print(json.dumps(report, indent=2))
