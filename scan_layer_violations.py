#!/usr/bin/env python3
"""Scan codebase for layer violations."""

import os
import re
from pathlib import Path
from collections import defaultdict

# Define layer mappings
LAYERS = {
    'adapters': 'Adapters (CLI)',
    'core': 'Core (Application)',
    'common': 'Common (Shared Utilities)',
    'shared': 'Shared (Infrastructure)',
    'infrastructure': 'Infrastructure',
}

# Define allowed dependencies
ALLOWED = {
    'adapters': {'core', 'common', 'shared', 'infrastructure'},
    'core': {'common', 'shared', 'infrastructure'},
    'common': {'shared', 'infrastructure'},
    'shared': set(),
    'infrastructure': set(),
}

violations = []

def get_layer(path_str):
    """Determine which layer a file belongs to."""
    parts = path_str.split(os.sep)
    if 'roadmap' not in parts:
        return None
    
    idx = parts.index('roadmap')
    if idx + 1 < len(parts):
        top_level = parts[idx + 1]
        if top_level in LAYERS:
            return top_level
    return None

def extract_imports(file_path):
    """Extract all imports from a Python file."""
    imports = []
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        for i, line in enumerate(lines, 1):
            # Match 'from X import Y' or 'import X'
            from_match = re.match(r'^\s*from\s+([\w\.]+)\s+import', line)
            import_match = re.match(r'^\s*import\s+([\w\.]+)', line)
            
            if from_match:
                imports.append((i, from_match.group(1)))
            elif import_match:
                imports.append((i, import_match.group(1)))
    except:
        pass
    
    return imports

def check_violation(from_layer, to_module):
    """Check if an import violates layer rules."""
    # Extract the top-level module from the import
    parts = to_module.split('.')
    if len(parts) < 2:
        return False
    
    to_layer = None
    for layer in LAYERS.keys():
        if parts[0] == 'roadmap' and len(parts) > 1 and parts[1] == layer:
            to_layer = layer
            break
    
    if not to_layer:
        return False
    
    # Check if this import is allowed
    if to_layer not in ALLOWED.get(from_layer, set()):
        return True
    
    return False

# Scan all Python files
roadmap_path = Path('roadmap')
for py_file in roadmap_path.rglob('*.py'):
    if '__pycache__' in str(py_file):
        continue
    
    from_layer = get_layer(str(py_file))
    if not from_layer:
        continue
    
    imports = extract_imports(str(py_file))
    
    for line_no, import_module in imports:
        if check_violation(from_layer, import_module):
            # Extract target layer
            parts = import_module.split('.')
            to_layer = parts[1] if len(parts) > 1 else None
            
            violations.append({
                'file': str(py_file),
                'line': line_no,
                'from_layer': from_layer,
                'import': import_module,
                'to_layer': to_layer
            })

# Sort violations by layer and file
violations.sort(key=lambda x: (x['from_layer'], x['file']))

# Print summary
print("=" * 80)
print("LAYER VIOLATION ANALYSIS")
print("=" * 80)
print()

if not violations:
    print("✅ No layer violations found!")
else:
    print(f"❌ Found {len(violations)} layer violations\n")
    
    # Group by source layer
    by_layer = defaultdict(list)
    for v in violations:
        by_layer[v['from_layer']].append(v)
    
    for layer in sorted(by_layer.keys()):
        violations_in_layer = by_layer[layer]
        print(f"\n{LAYERS[layer]} importing from forbidden layers ({len(violations_in_layer)} violations):")
        print("-" * 80)
        
        for v in violations_in_layer[:10]:  # Show first 10
            print(f"  {v['file']}:{v['line']}")
            print(f"    → from {v['import']}")
        
        if len(violations_in_layer) > 10:
            print(f"  ... and {len(violations_in_layer) - 10} more")

print()
print("=" * 80)
