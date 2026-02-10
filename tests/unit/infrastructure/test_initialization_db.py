"""Tests for initialization database behavior."""

import sqlite3

from roadmap.infrastructure.coordination.initialization import InitializationManager


def test_initialize_creates_project_database(tmp_path):
    manager = InitializationManager(root_path=tmp_path)

    manager.initialize()

    db_path = tmp_path / ".roadmap" / "db" / "state.db"
    assert db_path.exists()

    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS db_test (id INTEGER PRIMARY KEY, note TEXT)"
    )
    cursor = conn.execute("INSERT INTO db_test (note) VALUES (?)", ("ok",))
    row_id = cursor.lastrowid
    conn.commit()

    row = conn.execute("SELECT note FROM db_test WHERE id = ?", (row_id,)).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == "ok"
