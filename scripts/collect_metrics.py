#!/usr/bin/env python3
import ast
import os

rows = []
root_dir = os.path.join(os.path.dirname(__file__), "..", "roadmap")
root_dir = os.path.normpath(root_dir)

for root, _dirs, files in os.walk(root_dir):
    # skip virtualenvs
    if "/.venv" in root or "/venv" in root:
        continue
    for f in files:
        if not f.endswith(".py"):
            continue
        path = os.path.join(root, f)
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except Exception:
            continue
        loc = len(content.splitlines())
        try:
            tree = ast.parse(content)
        except Exception:
            class_count = 0
            max_methods = 0
        else:
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            class_count = len(classes)
            max_methods = 0
            for c in classes:
                mcount = sum(1 for n in c.body if isinstance(n, ast.FunctionDef))
                if mcount > max_methods:
                    max_methods = mcount
        rows.append((loc, class_count, max_methods, path))

rows.sort(reverse=True, key=lambda x: x[0])
for loc, cc, maxm, path in rows[:80]:
    print(f"{loc}\t{cc}\t{maxm}\t{path}")
