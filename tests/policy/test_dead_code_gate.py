"""Prove that the stock dead-code tool rejects high-confidence mistakes."""

import shutil
import subprocess

import pytest


@pytest.mark.parametrize(
    "source, diagnostic",
    [
        ("def sample():\n    return 1\n    print('unreachable')\n", "unreachable code"),
        ("def sample(forgotten):\n    return 2\n", "unused variable"),
    ],
)
def test_dead_code_gate_rejects_known_mistakes(tmp_path, source, diagnostic):
    path = tmp_path / "incorrect.py"
    path.write_text(source)
    executable = shutil.which("vulture")
    assert executable is not None
    result = subprocess.run(
        [executable, str(path), "--min-confidence", "100"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert diagnostic in result.stdout + result.stderr
