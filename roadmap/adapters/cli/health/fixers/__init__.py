"""Health check fixers for automatically correcting detected issues.

Available fixers:
- OldBackupsFixer: Delete old backup files (>90 days)
- DuplicateIssuesFixer: Merge duplicate issues
- OrphanedIssuesFixer: Assign unassigned issues to Backlog
- FolderStructureFixer: Move issues to correct milestone folders
- CorruptedCommentsFixer: Sanitize malformed JSON comments
"""
