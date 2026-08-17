"""Persistence Layer - Data Serialization and Storage.

This layer handles reading and writing data to files, including:
- YAML frontmatter parsing
- File locking mechanisms
- Database infrastructure management
- File synchronization

Modules:
- database_manager.py: SQLite connection and schema management
- file_synchronizer.py: File-to-database synchronization
- parser.py: Issue/Milestone/Project YAML frontmatter parsing
"""
