PRAGMA foreign_keys = ON;

CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  archived BOOLEAN DEFAULT 0,
  archived_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata TEXT
);

CREATE TABLE milestones (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  due_date DATE,
  progress_percentage REAL DEFAULT 0.0,
  archived BOOLEAN DEFAULT 0,
  archived_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  metadata TEXT,
  FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE issues (
  id TEXT PRIMARY KEY,
  project_id TEXT,
  milestone_id TEXT,
  title TEXT NOT NULL,
  headline TEXT DEFAULT '',
  description TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  priority TEXT NOT NULL DEFAULT 'medium',
  issue_type TEXT NOT NULL DEFAULT 'task',
  assignee TEXT,
  estimate_hours REAL,
  archived BOOLEAN DEFAULT 0,
  archived_at TIMESTAMP NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  due_date DATE,
  metadata TEXT,
  FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
  FOREIGN KEY (milestone_id) REFERENCES milestones (id) ON DELETE SET NULL
);

INSERT INTO projects (id, name, description, status, metadata)
VALUES ('c83ed497', 'Fixture Project', 'Sanitized compatibility project', 'active', '{"milestones":["v0-1-1"]}');

INSERT INTO milestones (id, project_id, title, description, status, due_date, progress_percentage, metadata)
VALUES ('v0-1-1', 'c83ed497', 'v0-1-1', 'Compatibility milestone', 'open', '2026-09-01', 50.0, '{}');

INSERT INTO issues (id, project_id, milestone_id, title, headline, description, status, priority, issue_type, assignee, estimate_hours, archived, archived_at, metadata)
VALUES
  ('951f146d', 'c83ed497', 'v0-1-1', 'Visible fixture issue', 'Exercise the released local workflow', 'Preserve user-authored Markdown.', 'in-progress', 'high', 'feature', 'fixture-user', 3.0, 0, NULL, '{"depends_on":["5898cb1f"],"remote_ids":{"github":101}}'),
  ('5898cb1f', 'c83ed497', 'v0-1-1', 'Closed dependency', 'Completed prerequisite retained for lifecycle checks', 'Legacy external reference.', 'closed', 'medium', 'other', 'fixture-user', 1.0, 0, NULL, '{"github_issue":77,"blocks":["951f146d"]}'),
  ('a11ce001', 'c83ed497', NULL, 'Archived fixture issue', 'Retained archived lifecycle state', 'Archived user content.', 'closed', 'low', 'other', NULL, NULL, 1, '2026-08-09T11:00:00+00:00', '{}');
