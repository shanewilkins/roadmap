# Known Issue: Semgrep + Import-Linter Dependency Conflict

We can't use the lastest semgrep or import-linter, because import-linter>2.6 requires rich > 14, and semgrep requires rich = 13.5. hopefully semgrep will update to latest rich soon. 
