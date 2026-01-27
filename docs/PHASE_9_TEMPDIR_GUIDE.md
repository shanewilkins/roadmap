"""Phase 9: Temporary Directory Refactoring Guide.

Shows practical before/after examples and prioritized refactoring targets.

This guide demonstrates:
1. How to use the new temp directory factories
2. Real-world before/after refactoring examples
3. Prioritized test files to refactor (highest ROI first)

Running this as a reference during refactoring helps maintain consistency.
"""

# =============================================================================
# EXAMPLE 1: TOML File Creation (from test_version_errors.py)
# =============================================================================

BEFORE_TOML = """
def test_get_current_version_from_pyproject(self, tmp_path):
    '''Test reading version from pyproject.toml.'''
    project_root = tmp_path
    pyproject_file = project_root / "pyproject.toml"

    # Write pyproject.toml
    pyproject_data = {"tool": {"poetry": {"version": "1.2.3"}}}
    with open(pyproject_file, "w") as f:
        toml.dump(pyproject_data, f)

    manager = VersionManager(project_root)
    version = manager.get_current_version()
    assert str(version) == "1.2.3"
"""

AFTER_TOML = """
def test_get_current_version_from_pyproject(self, tmp_path, temp_file_factory):
    '''Test reading version from pyproject.toml.'''
    # Factory handles file creation: more readable, easier to maintain
    temp_file_factory.create_toml(
        "pyproject.toml",
        tool={"poetry": {"version": "1.2.3"}}
    )

    manager = VersionManager(tmp_path)
    version = manager.get_current_version()
    assert str(version) == "1.2.3"
"""

# =============================================================================
# EXAMPLE 2: Git Repository Setup (from test_create_branch_edgecases.py)
# =============================================================================

BEFORE_GIT = """
def test_create_branch_fails_on_dirty_tree(tmp_path):
    '''Test that create_branch fails when working tree has uncommitted changes.'''
    # Initialize a real git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )

    # Create and commit a file
    (tmp_path / "README.md").write_text("# Repo")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmp_path, check=True)

    # Now create a modification
    (tmp_path / "modified_file.py").write_text("some code")
    subprocess.run(["git", "add", "modified_file.py"], cwd=tmp_path, check=True)

    g = GitIntegration(repo_path=tmp_path)
    issue = make_issue()
    success = g.create_branch_for_issue(issue)
    assert success is False
"""

AFTER_GIT = """
def test_create_branch_fails_on_dirty_tree(tmp_path, git_repo_factory):
    '''Test that create_branch fails when working tree has uncommitted changes.'''
    # Factory handles all setup: much cleaner and reusable
    git_repo_factory.create_repo()

    # Now create a modification
    (tmp_path / "modified_file.py").write_text("some code")
    subprocess.run(["git", "add", "modified_file.py"], cwd=tmp_path, check=True)

    g = GitIntegration(repo_path=tmp_path)
    issue = make_issue()
    success = g.create_branch_for_issue(issue)
    assert success is False
"""

# =============================================================================
# EXAMPLE 3: Roadmap Directory Structure (from multiple files)
# =============================================================================

BEFORE_ROADMAP = """
def test_sync_with_milestone_structure(tmp_path):
    '''Test sync with existing milestone structure.'''
    roadmap_dir = tmp_path / ".roadmap"
    roadmap_dir.mkdir()
    (roadmap_dir / "issues").mkdir()
    (roadmap_dir / "milestones").mkdir()

    # Create some issues
    issues_dir = roadmap_dir / "issues"
    for i in range(5):
        issue_file = issues_dir / f"ISSUE-{i}.md"
        issue_file.write_text(f"# Issue {i}\\nStatus: open")

    # Run sync
    syncer = DataSyncer(tmp_path)
    result = syncer.sync()
    assert result.success is True
"""

AFTER_ROADMAP = """
def test_sync_with_milestone_structure(tmp_path, roadmap_structure_factory):
    '''Test sync with existing milestone structure.'''
    # Factory creates entire structure with 5 issues: one line!
    roadmap_structure_factory.create_full_with_issues(5)

    # Run sync
    syncer = DataSyncer(tmp_path)
    result = syncer.sync()
    assert result.success is True
"""

# =============================================================================
# EXAMPLE 4: Isolated Workspace Context (reduces isolation pattern)
# =============================================================================

BEFORE_ISOLATION = """
def test_project_discovery(tmp_path):
    '''Test project discovery in isolated workspace.'''
    original_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # Create some project directories
        (tmp_path / "project1").mkdir()
        (tmp_path / "project1" / ".roadmap").mkdir()

        # Run discovery
        discoverer = ProjectDiscoverer()
        projects = discoverer.discover()
        assert len(projects) == 1
    finally:
        os.chdir(original_cwd)
"""

AFTER_ISOLATION = """
def test_project_discovery(tmp_path, isolated_workspace):
    '''Test project discovery in isolated workspace.'''
    with isolated_workspace:  # Auto restoration on exit
        # Create some project directories
        (tmp_path / "project1").mkdir()
        (tmp_path / "project1" / ".roadmap").mkdir()

        # Run discovery
        discoverer = ProjectDiscoverer()
        projects = discoverer.discover()
        assert len(projects) == 1
"""

# =============================================================================
# REFACTORING PRIORITY BY FILE (Top 8 to refactor)
# =============================================================================

REFACTORING_PRIORITY = """
================================================================================
PHASE 9 REFACTORING PRIORITY (Temporary Directory Pattern)
================================================================================

Tier 1 - HIGHEST ROI (15-20 min each):
  1. tests/unit/adapters/cli/services/test_export_manager.py (5 patterns)
     → Use: temp_file_factory
     → Expected savings: 5 hardcoded file operations

  2. tests/integration/git_hooks/test_git_hooks_workflow_integration.py (5 patterns)
     → Use: git_repo_factory + isolated_workspace
     → Expected savings: 5 git setup patterns

  3. tests/unit/cli/test_project_initialization_service.py (5 patterns)
     → Use: roadmap_structure_factory + temp_file_factory
     → Expected savings: 5 project setup patterns

  4. tests/unit/common/test_version_coverage.py (5 patterns)
     → Use: temp_file_factory (TOML/YAML creation)
     → Expected savings: 5 config file patterns

Tier 2 - HIGH ROI (15 min each):
  5. tests/unit/application/test_roadmap_core_comprehensive.py (4 patterns)
     → Use: roadmap_structure_factory

  6. tests/unit/application/test_health.py (4 patterns)
     → Use: isolated_workspace

  7. tests/unit/adapters/sync/test_sync_retrieval_orchestrator.py (4 patterns)
     → Use: roadmap_structure_factory

  8. tests/integration/core/test_core_entity_ops_comprehensive.py (4 patterns)
     → Use: roadmap_structure_factory

================================================================================
REFACTORING CHECKLIST PER FILE
================================================================================

For each file in priority order:

[ ] 1. Identify all tmp_path usage patterns in the file
[ ] 2. Determine which factory to use:
      - File creation → temp_file_factory
      - Git operations → git_repo_factory
      - .roadmap structure → roadmap_structure_factory
      - Directory isolation → isolated_workspace
[ ] 3. Add factory to test function signature (e.g., temp_file_factory)
[ ] 4. Replace hardcoded patterns with factory methods
[ ] 5. Run tests: pytest tests/path/to/test_file.py -v
[ ] 6. Verify all tests pass
[ ] 7. Commit: "Phase 9: Refactor temp dir usage in test_file.py"

================================================================================
QUICK REFERENCE: Factory Method Summary
================================================================================

temp_file_factory methods:
  .create_toml(filename, **kwargs)        → Create TOML config file
  .create_yaml(filename, **kwargs)        → Create YAML config file
  .create_file(filename, content)         → Create text file
  .create_python_module(name, content)    → Create Python module

git_repo_factory methods:
  .create_repo(initial_commit=True, ...)  → Init git repo with commit
  .create_with_branch(branch_name)        → Create repo with feature branch
  .create_with_file(filename, content)    → Create repo and add file

roadmap_structure_factory methods:
  .create_minimal()                       → Just .roadmap/issues & milestones
  .create_with_config(**config)           → Add config.yaml
  .create_full_with_issues(count)         → Populate with issue files

isolated_workspace methods:
  with isolated_workspace:                → Context manager (restores cwd)
  .change_to(subdir)                      → Change dir + create if needed
  .get_path(*parts)                       → Build path relative to root

================================================================================
TESTING YOUR CHANGES
================================================================================

After refactoring a file:

1. Run the specific file tests:
   pytest tests/path/to/refactored_file.py -v

2. Check if any assertions need updating:
   - Compare old tmp_path usage with new factory method
   - Verify returned Path objects are compatible

3. Full test suite:
   pytest tests/ -x  (stop on first failure)

4. Check for any import errors:
   pytest --collect-only tests/path/to/refactored_file.py

================================================================================
EXPECTED OUTCOMES
================================================================================

After completing Phase 9 Tier 1 refactoring:
- ✅ 4 files refactored (~20 hardcoded patterns eliminated)
- ✅ Tests remain functionally identical
- ✅ Future changes to temp setup are centralized in factories
- ✅ New tests can reuse proven patterns
- ✅ 2+ hours of refactoring effort = ~40 tests improved

Follow-up Phase 9 Tier 2:
- Refactor remaining 4 high-impact files
- Tackle mid-tier files (4 patterns each)
- Eventually convert 80+ test files using factories
"""

if __name__ == "__main__":
    print(REFACTORING_PRIORITY)
    print("\n" + "=" * 80)
    print("COPY-PASTE EXAMPLES")
    print("=" * 80)
    print("\nBEFORE (TOML):")
    print(BEFORE_TOML)
    print("\nAFTER (TOML):")
    print(AFTER_TOML)
    print("\nBEFORE (GIT):")
    print(BEFORE_GIT)
    print("\nAFTER (GIT):")
    print(AFTER_GIT)
    print("\nBEFORE (ROADMAP):")
    print(BEFORE_ROADMAP)
    print("\nAFTER (ROADMAP):")
    print(AFTER_ROADMAP)
    print("\nBEFORE (ISOLATION):")
    print(BEFORE_ISOLATION)
    print("\nAFTER (ISOLATION):")
    print(AFTER_ISOLATION)
