"""Verification must have scoped evidence; approved work may remain unverified."""

import csv
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from tests.policy.test_cli_behavior_matrix import _test_ids

ROOT = Path(__file__).resolve().parents[2]
LEDGER = "docs/requirements/verification-evidence.json"


def _validate_verified(row, entry):
    assert entry is not None, f"{row['id']}: missing verification record"
    assert entry["result"] == "verified", f"{row['id']}: evidence is not passing"
    assert entry["scope"], f"{row['id']}: missing scope"
    assert date.fromisoformat(entry["checked_at"]) <= date.today()
    assert not entry["remaining"], f"{row['id']}: unmet criteria remain"
    assert entry["tests"] and entry["commands"], f"{row['id']}: missing evidence"
    assert LEDGER in row["source"].split("; "), f"{row['id']}: unlinked evidence"


def test_verified_requirements_have_passing_traceable_candidate_evidence():
    ledger = json.loads((ROOT / LEDGER).read_text())
    assert ledger["schema_version"] == 1
    assert ledger["baseline_commit"] and ledger["candidate_scope"]
    rows = {}
    for name in ("user", "technical"):
        with (ROOT / f"docs/requirements/{name}-requirements.csv").open(
            newline=""
        ) as stream:
            rows.update((row["id"], row) for row in csv.DictReader(stream))
    cache = {}
    for identity, entry in ledger["requirements"].items():
        assert identity in rows
        assert entry["result"] in {"verified", "partial"}
        assert entry["scope"] and entry["commands"] and entry["tests"]
        assert date.fromisoformat(entry["checked_at"]) <= date.today()
        if entry["result"] == "verified":
            assert rows[identity]["status"] == "Verified"
        else:
            assert entry["remaining"]
            assert rows[identity]["status"] == "Accepted"
        for reference in entry["tests"]:
            filename, identifier = reference.split("::", 1)
            if filename not in cache:
                cache[filename] = _test_ids(ROOT / filename)
            assert identifier in cache[filename], reference
    for identity, row in rows.items():
        if row["status"] == "Verified":
            _validate_verified(row, ledger["requirements"].get(identity))


@pytest.mark.parametrize(
    "damage", ["missing", "partial", "gap", "scope", "tests", "commands", "unlinked"]
)
def test_verification_gate_rejects_unsubstantiated_verified_status(damage):
    ledger = json.loads((ROOT / LEDGER).read_text())
    entry = deepcopy(ledger["requirements"]["TR-003"])
    row = {"id": "TR-003", "source": LEDGER}
    if damage == "missing":
        entry = None
    elif damage == "partial":
        entry["result"] = "partial"
    elif damage == "gap":
        entry["remaining"] = ["missing acceptance proof"]
    elif damage == "unlinked":
        row["source"] = ""
    else:
        entry[damage] = [] if damage in {"tests", "commands"} else ""
    with pytest.raises(AssertionError):
        _validate_verified(row, entry)
