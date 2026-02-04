# Vulture 60% Confidence Findings - Review List

Generated: February 3, 2026
Total Items: 434

This file tracks all potential dead code findings at 60% confidence level.
Items can be categorized as:
- **FALSE_POSITIVE**: CLI commands, provider functions, interface methods → add `# noqa: F841`
- **UNUSED**: Actually dead code → remove
- **REVIEW**: Needs manual inspection

---

## Category: CLI Command Handlers (Auto-registered via Click)
These are Click command handlers registered via decorators. They appear unused to static analysis
but are actually called by Click's command routing. Mark with `# noqa: F841`

### Archive Operations
- roadmap/adapters/cli/archive_operations.py:13: unused function 'handle_archive_parse_error'
- roadmap/adapters/cli/archive_operations.py:51: unused function 'handle_restore_parse_error'

### Comment Commands
- roadmap/adapters/cli/comment/commands.py:65: unused function 'edit_comment'
- roadmap/adapters/cli/comment/commands.py:88: unused function 'delete_comment'

### Config Commands
- roadmap/adapters/cli/config/commands.py:18: unused function 'view'
- roadmap/adapters/cli/config/commands.py:68: unused function 'get_cmd'
- roadmap/adapters/cli/config/commands.py:86: unused function 'set_cmd'

### Data Commands
- roadmap/adapters/cli/data/commands.py:133: unused function 'generate_report'

### Git Commands
- roadmap/adapters/cli/git/commands.py:39: unused function 'setup_git'
- roadmap/adapters/cli/git/commands.py:148: unused function 'hooks_status'
- roadmap/adapters/cli/git/commands.py:162: unused function 'sync_git'
- roadmap/adapters/cli/git/commands.py:366: unused function 'git_status'
- roadmap/adapters/cli/git/commands.py:484: unused function 'git_link'

### Issues Commands
- roadmap/adapters/cli/issues/deps.py:21: unused function 'add_dependency'

### Sync Commands
- roadmap/adapters/cli/sync.py:253: unused function 'sync'

### Validation
- roadmap/adapters/cli/sync_validation.py:18: unused function 'validate_links'

---

## Category: CLI Helper Functions
Used internally by CLI commands or dynamically

### CLI Command Helpers
- roadmap/adapters/cli/__init__.py:161: unused function '_detect_project_context'
- roadmap/adapters/cli/cli_command_helpers.py:91: unused function 'confirm_action'
- roadmap/adapters/cli/cli_confirmations.py:22: unused function 'check_entity_exists'
- roadmap/adapters/cli/cli_confirmations.py:59: unused function 'confirm_action'

### CRUD Validators
- roadmap/adapters/cli/crud/entity_builders.py:17: unused method 'validate_issue_exists'
- roadmap/adapters/cli/crud/entity_builders.py:197: unused method 'validate_milestone_exists'
- roadmap/adapters/cli/crud/entity_builders.py:298: unused method 'validate_project_exists'

### CLI Decorators
- roadmap/adapters/cli/decorators.py:156: unused function 'add_output_flags'

### Exception Handlers
- roadmap/adapters/cli/exception_handler.py:50: unused function 'with_exception_handler'
- roadmap/adapters/cli/exception_handler.py:89: unused function 'setup_cli_exception_handling'
- roadmap/adapters/cli/exception_handler.py:99: unused function 'handle_exception'

### Git Helper Functions
- roadmap/adapters/cli/git/commands.py:418: unused function '_validate_branch_environment'
- roadmap/adapters/cli/git/commands.py:431: unused function '_get_and_validate_issue'

### Sync Helper Functions
- roadmap/adapters/cli/sync.py:19: unused function '_show_baseline'
- roadmap/adapters/cli/sync.py:26: unused function '_reset_baseline'
- roadmap/adapters/cli/sync.py:112: unused function '_capture_and_save_post_sync_baseline'
- roadmap/adapters/cli/sync.py:123: unused function '_perform_apply_phase'
- roadmap/adapters/cli/sync.py:201: unused function '_clear_baseline'
- roadmap/adapters/cli/sync.py:208: unused function '_show_conflicts'
- roadmap/adapters/cli/sync.py:215: unused function '_handle_link_unlink'

### Click Options
- roadmap/adapters/cli/utils/click_options.py:36: unused function 'health_check_options'

---

## Category: CLI Output & Formatting
Display and presentation methods

### Layout
- roadmap/adapters/cli/layout.py:21: unused variable 'min_column_width'
- roadmap/adapters/cli/layout.py:22: unused variable 'max_horizontal_width'
- roadmap/adapters/cli/layout.py:194: unused method 'render_as_string'

### Output Manager
- roadmap/adapters/cli/output_manager.py:177: unused method 'render_table'
- roadmap/adapters/cli/output_manager.py:219: unused method 'render_rich'
- roadmap/adapters/cli/output_manager.py:242: unused method 'print_message'
- roadmap/adapters/cli/output_manager.py:266: unused method 'print_styled'
- roadmap/adapters/cli/output_manager.py:289: unused method 'print_section_header'
- roadmap/adapters/cli/output_manager.py:302: unused function 'create_output_manager'

### Issues Update
- roadmap/adapters/cli/issues/update.py:24: unused attribute '_current_reason'
- roadmap/adapters/cli/issues/update.py:47: unused attribute '_current_reason'

### Presentation Layer
Base Presenter Methods:
- roadmap/adapters/cli/presentation/base_presenter.py:68: unused method '_render_section'
- roadmap/adapters/cli/presentation/base_presenter.py:80: unused method '_render_footer'
- roadmap/adapters/cli/presentation/base_presenter.py:93: unused method '_render_warning'
- roadmap/adapters/cli/presentation/base_presenter.py:103: unused method '_render_error'
- roadmap/adapters/cli/presentation/base_presenter.py:113: unused method '_render_success'

Core Initialization Presenter:
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:43: unused method 'present_initialization_error'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:100: unused method 'present_status_header'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:105: unused method 'present_status_section'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:110: unused method 'present_status_item'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:116: unused method 'present_status_not_initialized'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:128: unused method 'present_health_section'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:133: unused method 'present_health_check'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:165: unused method 'present_overall_health'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:194: unused method 'present_health_warning'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:225: unused method 'present_warning'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:229: unused method 'present_info'
- roadmap/adapters/cli/presentation/core_initialization_presenter.py:233: unused method 'present_success'

CRUD Presenters:
- roadmap/adapters/cli/presentation/crud_presenter.py:137: unused class 'ArchivePresenter'
- roadmap/adapters/cli/presentation/crud_presenter.py:157: unused class 'RestorePresenter'

Milestone List Presenter:
- roadmap/adapters/cli/presentation/milestone_list_presenter.py:93: unused method 'show_no_upcoming_milestones'
- roadmap/adapters/cli/presentation/milestone_list_presenter.py:102: unused method 'show_milestones_list'

Project Status Presenter:
- roadmap/adapters/cli/presentation/project_status_presenter.py:151: unused method 'show_roadmap_summary'

Table Builders:
- roadmap/adapters/cli/presentation/table_builders.py:67: unused function 'create_panel'

---

## Category: CLI Services
Service layer for CLI operations

### Daily Summary Service
- roadmap/adapters/cli/services/daily_summary_service.py:253: unused method 'get_next_action_suggestion'

### Milestone List Service
- roadmap/adapters/cli/services/milestone_list_service.py:227: unused method 'get_milestone_due_date_status'

### Project Status Service
- roadmap/adapters/cli/services/project_status_service.py:138: unused method 'get_status_styling'
- roadmap/adapters/cli/services/project_status_service.py:197: unused class 'RoadmapSummaryService'
- roadmap/adapters/cli/services/project_status_service.py:200: unused method 'compute_roadmap_summary'

---

## Category: Git Adapter
Git integration functionality

### Git Hooks Manager
- roadmap/adapters/git/git_hooks_manager.py:76: unused method 'get_hook_config'
- roadmap/adapters/git/git_hooks_manager.py:91: unused method 'handle_post_commit'
- roadmap/adapters/git/git_hooks_manager.py:118: unused method 'handle_post_checkout'
- roadmap/adapters/git/git_hooks_manager.py:148: unused method 'handle_pre_push'
- roadmap/adapters/git/git_hooks_manager.py:176: unused method 'handle_post_merge'
- roadmap/adapters/git/git_hooks_manager.py:219: unused method '_update_issue_from_commit'
- roadmap/adapters/git/git_hooks_manager.py:260: unused method '_complete_issue_from_commit'
- roadmap/adapters/git/git_hooks_manager.py:271: unused attribute 'completed_date'

### Hook Registry
- roadmap/adapters/git/hook_registry.py:44: unused method 'get_hook_file'

### Sync Monitor
- roadmap/adapters/git/sync_monitor.py:403: unused method 'clear_cache'

### Workflow Automation
- roadmap/adapters/git/workflow_automation.py:33: unused method 'setup_automation'
- roadmap/adapters/git/workflow_automation.py:59: unused method 'disable_automation'
- roadmap/adapters/git/workflow_automation.py:136: unused method 'sync_all_issues_with_git'
- roadmap/adapters/git/workflow_automation.py:280: unused attribute 'completed_date'

---

## Category: GitHub Adapter
GitHub API integration

### GitHub Sync Backend
- roadmap/adapters/github/github.py:117: unused method 'status_to_labels'
- roadmap/adapters/github/github.py:135: unused method 'labels_to_status'

### GitHub Comments Handler
- roadmap/adapters/github/handlers/comments.py:33: unused method 'get_issue_comments'
- roadmap/adapters/github/handlers/comments.py:57: unused method 'create_issue_comment'
- roadmap/adapters/github/handlers/comments.py:82: unused method 'update_issue_comment'
- roadmap/adapters/github/handlers/comments.py:106: unused method 'delete_issue_comment'

### GitHub Issues Handler
- roadmap/adapters/github/handlers/issues.py:118: unused method 'reopen_issue'

### GitHub Labels Handler
- roadmap/adapters/github/handlers/labels.py:38: unused method 'update_label'
- roadmap/adapters/github/handlers/labels.py:62: unused method 'delete_label'
- roadmap/adapters/github/handlers/labels.py:69: unused method 'priority_to_labels'
- roadmap/adapters/github/handlers/labels.py:79: unused method 'status_to_labels'
- roadmap/adapters/github/handlers/labels.py:90: unused method 'labels_to_priority'
- roadmap/adapters/github/handlers/labels.py:109: unused method 'labels_to_status'

---

## Category: Persistence/Storage
Database and file storage operations

### Conflict Resolution
- roadmap/adapters/persistence/conflict_resolver.py:149: unused method 'auto_resolve_conflicts'
- roadmap/adapters/persistence/conflict_resolver.py:178: unused method 'get_conflict_summary'

### Database Manager
- roadmap/adapters/persistence/database_manager.py:64: unused attribute 'row_factory'

### File Locking
- roadmap/adapters/persistence/file_locking.py:202: unused method 'is_file_locked'
- roadmap/adapters/persistence/file_locking.py:212: unused method 'force_unlock_file'
- roadmap/adapters/persistence/file_locking.py:217: unused method 'cleanup_stale_locks'
- roadmap/adapters/persistence/file_locking.py:242: unused method 'get_all_locks'
- roadmap/adapters/persistence/file_locking.py:276: unused method 'read_file_locked'
- roadmap/adapters/persistence/file_locking.py:323: unused method 'update_file_locked'
- roadmap/adapters/persistence/file_locking.py:348: unused variable 'locked_file_ops'

### Focused Managers
- roadmap/adapters/persistence/focused_managers.py:19: unused class 'FocusedProjectStateManager'
- roadmap/adapters/persistence/focused_managers.py:51: unused class 'FocusedMilestoneStateManager'
- roadmap/adapters/persistence/focused_managers.py:75: unused class 'FocusedIssueStateManager'
- roadmap/adapters/persistence/focused_managers.py:103: unused class 'FocusedSyncStateManager'
- roadmap/adapters/persistence/focused_managers.py:119: unused class 'FocusedQueryStateManager'

### Git History
- roadmap/adapters/persistence/git_history.py:214: unused function 'get_file_at_head'
- roadmap/adapters/persistence/git_history.py:232: unused function 'get_last_modified_time'
- roadmap/adapters/persistence/git_history.py:280: unused function 'get_repository_root'

### Parsers
Issue Parser Safe Methods:
- roadmap/adapters/persistence/parser/issue.py:208: unused method 'parse_issue_file_safe'
- roadmap/adapters/persistence/parser/issue.py:233: unused method 'save_issue_file_safe'

Milestone Parser Safe Methods:
- roadmap/adapters/persistence/parser/milestone.py:105: unused method 'parse_milestone_file_safe'
- roadmap/adapters/persistence/parser/milestone.py:127: unused method 'save_milestone_file_safe'

### Persistence Main
- roadmap/adapters/persistence/persistence.py:39: unused method 'list_backups'

### Repositories
Remote Link Repository:
- roadmap/adapters/persistence/repositories/remote_link_repository.py:74: unused method 'unlink_issue'
- roadmap/adapters/persistence/repositories/remote_link_repository.py:183: unused method 'get_all_links_for_issue'
- roadmap/adapters/persistence/repositories/remote_link_repository.py:257: unused method 'validate_link'
- roadmap/adapters/persistence/repositories/remote_link_repository.py:338: unused method 'clear_all'

Sync State Repository:
- roadmap/adapters/persistence/repositories/sync_state_repository.py:62: unused method 'clear_all'

### State Manager
- roadmap/adapters/persistence/storage/state_manager.py:68: unused attribute '_sync_state_tracker'
- roadmap/adapters/persistence/storage/state_manager.py:69: unused attribute '_conflict_resolver'
- roadmap/adapters/persistence/storage/state_manager.py:141: unused method '_initialize_remote_links_from_yaml'
- roadmap/adapters/persistence/storage/state_manager.py:259: unused method 'get_issue_repository'
- roadmap/adapters/persistence/storage/state_manager.py:268: unused method 'get_milestone_repository'
- roadmap/adapters/persistence/storage/state_manager.py:277: unused method 'get_project_repository'
- roadmap/adapters/persistence/storage/state_manager.py:515: unused method 'clear_sync_baseline'

### Sync State Tracker
- roadmap/adapters/persistence/sync_state_tracker.py:74: unused method 'get_last_full_rebuild'

---

## Category: Sync Adapter
Sync orchestration and merging

### GitHub Client
- roadmap/adapters/sync/backends/github_client.py:44: unused attribute '_owner'
- roadmap/adapters/sync/backends/github_client.py:45: unused attribute '_repo'

### GitHub Sync Backend
- roadmap/adapters/sync/backends/github_sync_backend.py:87: unused attribute 'conflict_detector'
- roadmap/adapters/sync/backends/github_sync_backend.py:89: unused attribute 'conflict_detector'
- roadmap/adapters/sync/backends/github_sync_backend.py:112: unused attribute '_push_service'

### GitHub Issue Push Service
- roadmap/adapters/sync/backends/services/github_issue_push_service.py:14: unused class 'GitHubIssuePushService'

### Sync Services
Issue Persistence Service:
- roadmap/adapters/sync/services/issue_persistence_service.py:52: unused method 'update_github_issue_number'
- roadmap/adapters/sync/services/issue_persistence_service.py:124: unused method 'apply_sync_issue_to_local'
- roadmap/adapters/sync/services/issue_persistence_service.py:167: unused method 'get_issue_from_repo'
- roadmap/adapters/sync/services/issue_persistence_service.py:206: unused method 'is_github_linked'
- roadmap/adapters/sync/services/issue_persistence_service.py:224: unused method 'get_github_issue_number'

Issue State Service:
- roadmap/adapters/sync/services/issue_state_service.py:22: unused method 'sync_issue_to_issue'
- roadmap/adapters/sync/services/issue_state_service.py:117: unused method 'issue_to_push_payload'

Sync Linking Service:
- roadmap/adapters/sync/services/sync_linking_service.py:198: unused method 'get_local_id_from_remote'
- roadmap/adapters/sync/services/sync_linking_service.py:272: unused method 'link_sync_issue'
- roadmap/adapters/sync/services/sync_linking_service.py:300: unused method 'is_linked'

### Sync Cache Orchestrator
- roadmap/adapters/sync/sync_cache_orchestrator.py:45: unused attribute 'optimized_builder'
- roadmap/adapters/sync/sync_cache_orchestrator.py:388: unused method 'capture_post_sync_baseline'

### Sync Merge Engine
- roadmap/adapters/sync/sync_merge_engine.py:87: unused method '_filter_unchanged_issues_from_base'

### Sync Merge Orchestrator
- roadmap/adapters/sync/sync_merge_orchestrator.py:272: unused method '_filter_unchanged_issues_from_base'

### Sync Retrieval Orchestrator
- roadmap/adapters/sync/sync_retrieval_orchestrator.py:59: unused method 'list_files_in_directory'
- roadmap/adapters/sync/sync_retrieval_orchestrator.py:76: unused attribute 'sync_metadata_cache'
- roadmap/adapters/sync/sync_retrieval_orchestrator.py:137: unused method 'ensure_baseline'

---

## Category: Common/Utilities
Shared utility functions and helpers

### Cache
- roadmap/common/cache.py:110: unused method 'invalidate'
- roadmap/common/cache.py:164: unused function 'clear_session_cache'
- roadmap/common/cache.py:178: unused function 'cache_result'

### CLI Errors
- roadmap/common/cli_errors.py:132: unused function 'validate_required_args'

### Configuration Schema
- roadmap/common/configuration/config_schema.py:39: unused variable 'logs_dir'
- roadmap/common/configuration/config_schema.py:59: unused variable 'sync_enabled'
- roadmap/common/configuration/config_schema.py:61: unused variable 'webhook_secret'
- roadmap/common/configuration/config_schema.py:62: unused variable 'sync_settings'
- roadmap/common/configuration/config_schema.py:80: unused variable 'default_milestone'
- roadmap/common/configuration/config_schema.py:91: unused variable 'auto_branch_on_start'
- roadmap/common/configuration/config_schema.py:92: unused variable 'confirm_destructive'
- roadmap/common/configuration/config_schema.py:93: unused variable 'show_tips'
- roadmap/common/configuration/config_schema.py:94: unused variable 'include_closed_in_critical_path'

### Constants
Status Constants:
- roadmap/common/constants.py:37: unused variable 'ON_HOLD'
- roadmap/common/constants.py:39: unused variable 'CANCELLED'

Backend Constants:
- roadmap/common/constants.py:62: unused variable 'GIT'

Validation Constants:
- roadmap/common/constants.py:132: unused variable 'VALIDATION_DESCRIPTION_MAX_LENGTH'

### Error Formatting
- roadmap/common/error_formatter.py:36: unused function 'format_warning_message'
- roadmap/common/error_formatter.py:53: unused function 'format_info_message'
- roadmap/common/error_formatter.py:70: unused function 'format_success_message'

### Error Classes
Error Base:
- roadmap/common/errors/error_base.py:25: unused variable 'GITHUB_API'
- roadmap/common/errors/error_base.py:29: unused variable 'DEPENDENCY'
- roadmap/common/errors/error_base.py:30: unused variable 'USER_INPUT'

Error Handler:
- roadmap/common/errors/error_handler.py:126: unused method 'get_error_summary'

Error Standards:
- roadmap/common/errors/error_standards.py:55: unused variable 'IMPORT'
- roadmap/common/errors/error_standards.py:56: unused variable 'EXPORT'
- roadmap/common/errors/error_standards.py:57: unused variable 'VALIDATE'
- roadmap/common/errors/error_standards.py:58: unused variable 'AUTHENTICATE'
- roadmap/common/errors/error_standards.py:59: unused variable 'FETCH'
- roadmap/common/errors/error_standards.py:110: unused method 'with_state'
- roadmap/common/errors/error_standards.py:116: unused method 'with_recovery'
- roadmap/common/errors/error_standards.py:123: unused method 'with_attempt'
- roadmap/common/errors/error_standards.py:449: unused method 'retry_with_backoff'
- roadmap/common/errors/error_standards.py:487: unused method 'is_retryable'
- roadmap/common/errors/error_standards.py:499: unused method 'handle_missing_file'
- roadmap/common/errors/error_standards.py:527: unused method 'handle_permission_error'
- roadmap/common/errors/error_standards.py:539: unused method 'handle_connection_error'

### Formatters
Helpers:
- roadmap/common/formatters/helpers.py:14: unused function '__getattr__'

Kanban Layout:
- roadmap/common/formatters/kanban/layout.py:25: unused method 'format_issue_cell'

Table Formatters:
- roadmap/common/formatters/tables/column_factory.py:281: unused function 'create_milestone_columns'
- roadmap/common/formatters/tables/issue_table.py:212: unused method 'create_issue_table'
- roadmap/common/formatters/tables/issue_table.py:217: unused method 'add_issue_row'
- roadmap/common/formatters/tables/issue_table.py:222: unused method 'display_issues'

Text Formatters:
- roadmap/common/formatters/text/operations.py:55: unused method 'failure'
- roadmap/common/formatters/text/operations.py:298: unused function 'print_operation_success'
- roadmap/common/formatters/text/operations.py:315: unused function 'print_operation_failure'

### Output Formatting
- roadmap/common/output_formatter.py:380: unused class 'HTMLOutputFormatter'

### Progress
- roadmap/common/progress.py:158: unused method 'recalculate_all_progress'
- roadmap/common/progress.py:313: unused method 'register_listener'
- roadmap/common/progress.py:321: unused method 'on_issue_updated'

### Status Styles
- roadmap/common/status_style_manager.py:14: unused class 'StatusStyle'
- roadmap/common/status_style_manager.py:24: unused variable 'ARCHIVED'
- roadmap/common/status_style_manager.py:69: unused method 'get_emoji'
- roadmap/common/status_style_manager.py:82: unused method 'get_rich_text'
- roadmap/common/status_style_manager.py:98: unused method 'all_styles'
- roadmap/common/status_style_manager.py:107: unused method 'all_emojis'

### GitHub Setup Validator
- roadmap/common/initialization/github/setup_validator.py:65: unused method 'test_api_access'

### Logging/Performance
- roadmap/common/logging/performance_tracking.py:219: unused method 'start_step'
- roadmap/common/logging/performance_tracking.py:245: unused method 'finish'

### Models
Config Models:
- roadmap/common/models/config_models.py:25: unused variable 'model_config'
- roadmap/common/models/config_models.py:47: unused variable 'model_config'
- roadmap/common/models/config_models.py:53: unused variable 'auto_branch_on_start'
- roadmap/common/models/config_models.py:57: unused variable 'confirm_destructive'
- roadmap/common/models/config_models.py:61: unused variable 'show_tips'
- roadmap/common/models/config_models.py:65: unused variable 'include_closed_in_critical_path'
- roadmap/common/models/config_models.py:73: unused variable 'model_config'
- roadmap/common/models/config_models.py:79: unused variable 'auto_commit'
- roadmap/common/models/config_models.py:83: unused variable 'commit_template'
- roadmap/common/models/config_models.py:87: unused variable 'model_config'
- roadmap/common/models/config_models.py:109: unused variable 'sync_enabled'
- roadmap/common/models/config_models.py:117: unused variable 'webhook_secret'
- roadmap/common/models/config_models.py:121: unused variable 'sync_settings'
- roadmap/common/models/config_models.py:130: unused variable 'model_config'
- roadmap/common/models/config_models.py:141: unused variable 'model_config'

Output Models:
- roadmap/common/models/output_models.py:21: unused variable 'DATETIME'

### Metrics & Profiling
Metrics:
- roadmap/common/services/metrics.py:107: unused method 'get_error_rate'
- roadmap/common/services/metrics.py:117: unused method 'get_operation_stats'

Profiling:
- roadmap/common/services/profiling.py:133: unused method 'get_profile'
- roadmap/common/services/profiling.py:144: unused method 'get_slowest_operations'
- roadmap/common/services/profiling.py:158: unused method 'get_report'
- roadmap/common/services/profiling.py:248: unused method 'get_dict'

### Retry Policy
- roadmap/common/services/retry.py:258: unused method 'async_decorator'

### Status Utils
- roadmap/common/utils/status_utils.py:49: unused method 'count_by_status'
- roadmap/common/utils/status_utils.py:71: unused method 'summarize_checks'

### Timezone Utils
- roadmap/common/utils/timezone_utils.py:335: unused method 'make_aware'
- roadmap/common/utils/timezone_utils.py:351: unused method 'get_common_timezones'

### Validation
Roadmap Validator:
- roadmap/common/validation/roadmap_validator.py:166: unused method 'validate_required_fields'
- roadmap/common/validation/roadmap_validator.py:182: unused method 'validate_enum_field'
- roadmap/common/validation/roadmap_validator.py:201: unused method 'validate_string_length'
- roadmap/common/validation/roadmap_validator.py:224: unused method 'validate_id_format'
- roadmap/common/validation/roadmap_validator.py:271: unused method 'validate_github_issue_number'
- roadmap/common/validation/roadmap_validator.py:289: unused method 'validate_labels'

Validators:
- roadmap/common/validation/validators.py:14: unused variable 'REQUIRED'
- roadmap/common/validation/validators.py:15: unused variable 'FORMAT'
- roadmap/common/validation/validators.py:16: unused variable 'RANGE'
- roadmap/common/validation/validators.py:18: unused variable 'LENGTH'
- roadmap/common/validation/validators.py:19: unused variable 'PATTERN'
- roadmap/common/validation/validators.py:20: unused variable 'CUSTOM'

---

## Category: Core Domain
Domain models and entities

### Comment
- roadmap/core/domain/comment.py:17: unused variable 'github_url'

### Issue
- roadmap/core/domain/issue.py:23: unused variable 'model_config'
- roadmap/core/domain/issue.py:59: unused variable 'completed_date'
- roadmap/core/domain/issue.py:70: unused method 'migrate_github_issue_to_remote_ids'
- roadmap/core/domain/issue.py:157: unused method 'model_dump_json'
- roadmap/core/domain/issue.py:191: unused property 'is_started'
- roadmap/core/domain/issue.py:252: unused property 'handoff_context_summary'

### Milestone
- roadmap/core/domain/milestone.py:33: unused variable 'github_milestone'
- roadmap/core/domain/milestone.py:66: unused method 'get_issue_count'
- roadmap/core/domain/milestone.py:122: unused method 'get_remaining_estimated_hours'

### Project
- roadmap/core/domain/project.py:32: unused variable 'repo_url'
- roadmap/core/domain/project.py:66: unused method 'get_milestone_count'

---

## Category: Core Interfaces (Protocol Methods)
These are protocol/interface method definitions. Should be ignored in .vultureignore

### Credentials Interface
- roadmap/core/interfaces/__init__.py:95: unused method 'delete_token'
- roadmap/core/interfaces/__init__.py:103: unused method 'is_available'

### Backend Factory
- roadmap/core/interfaces/backend_factory.py:17: unused method 'create_backend'
- roadmap/core/interfaces/backend_factory.py:37: unused method 'list_supported_backends'
- roadmap/core/interfaces/backend_factory.py:46: unused method 'get_default_backend'

### GitHub Interface
- roadmap/core/interfaces/github.py:92: unused method 'validate_credentials'

### Parsers Interface
- roadmap/core/interfaces/parsers.py:34: unused method 'parse_issue_content'
- roadmap/core/interfaces/parsers.py:66: unused method 'parse_milestone_content'
- roadmap/core/interfaces/parsers.py:98: unused method 'parse_project_content'

### Persistence Interface
- roadmap/core/interfaces/persistence.py:42: unused method 'list_files_in_directory'

### Repositories Interface
- roadmap/core/interfaces/repositories.py:55: unused method 'bulk_update'
- roadmap/core/interfaces/repositories.py:60: unused method 'find_by_milestone'
- roadmap/core/interfaces/repositories.py:65: unused method 'find_by_status'
- roadmap/core/interfaces/repositories.py:113: unused method 'find_by_status'
- roadmap/core/interfaces/repositories.py:146: unused method 'get_current'
- roadmap/core/interfaces/repositories.py:166: unused method 'get_status'

### State Storage Interface
- roadmap/core/interfaces/state_storage.py:24: unused method 'save_sync_state'
- roadmap/core/interfaces/state_storage.py:36: unused method 'clear_sync_state'
- roadmap/core/interfaces/state_storage.py:45: unused method 'get_last_sync_time'
- roadmap/core/interfaces/state_storage.py:54: unused method 'update_last_sync_time'

### Sync Services Interface
- roadmap/core/interfaces/sync_services.py:16: unused method 'link_issues'
- roadmap/core/interfaces/sync_services.py:29: unused method 'unlink_issue'
- roadmap/core/interfaces/sync_services.py:41: unused method 'get_linked_remote_id'
- roadmap/core/interfaces/sync_services.py:53: unused method 'get_linked_local_id'
- roadmap/core/interfaces/sync_services.py:72: unused method 'cache_remote_issue'
- roadmap/core/interfaces/sync_services.py:85: unused method 'get_cached_remote_issue'
- roadmap/core/interfaces/sync_services.py:97: unused method 'invalidate_cache'
- roadmap/core/interfaces/sync_services.py:109: unused method 'is_cache_fresh'

---

## Category: Core Models
- roadmap/core/models.py:60: unused class 'IssueQueryParams'
- roadmap/core/models.py:73: unused variable 'offset'
- roadmap/core/models.py:76: unused class 'MilestoneCreateServiceParams'
- roadmap/core/models.py:85: unused class 'MilestoneUpdateServiceParams'

---

## Category: Core Services
Application service layer

### Baseline Services
- roadmap/core/services/baseline/baseline_builder_progress.py:43: unused attribute '_current_task'
- roadmap/core/services/baseline/baseline_retriever.py:20: unused method 'get_current_baseline'
- roadmap/core/services/baseline/baseline_selector.py:46: unused method 'get_baseline_for_issue'
- roadmap/core/services/baseline/optimized_baseline_builder.py:344: unused method 'estimate_rebuild_time'

### Comment Service
- roadmap/core/services/comment/comment_service.py:197: unused method 'validate_comment_thread'

### Git Hook Auto Sync
- roadmap/core/services/git/git_hook_auto_sync_service.py:125: unused method 'auto_sync_on_commit'
- roadmap/core/services/git/git_hook_auto_sync_service.py:146: unused method 'auto_sync_on_checkout'
- roadmap/core/services/git/git_hook_auto_sync_service.py:167: unused method 'auto_sync_on_merge'

### GitHub Services
Change Detector:
- roadmap/core/services/github/github_change_detector.py:11: unused class 'GitHubChangeDetector'
- roadmap/core/services/github/github_change_detector.py:22: unused method 'detect_issue_changes'
- roadmap/core/services/github/github_change_detector.py:84: unused method 'detect_milestone_changes'

Config Validator:
- roadmap/core/services/github/github_config_validator.py:12: unused class 'GitHubConfigValidator'

Conflict Detector:
- roadmap/core/services/github/github_conflict_detector.py:160: unused method 'get_conflict_summary'

Entity Classifier:
- roadmap/core/services/github/github_entity_classifier.py:8: unused class 'GitHubEntityClassifier'
- roadmap/core/services/github/github_entity_classifier.py:32: unused method 'separate_by_state'

Integration Service:
- roadmap/core/services/github/github_integration_service.py:412: unused method 'get_last_canonical_assignee'
- roadmap/core/services/github/github_integration_service.py:420: unused method 'clear_cache'

Issue Client:
- roadmap/core/services/github/github_issue_client.py:181: unused method 'get_issue_diff'

### Health Services
Data Integrity Validator:
- roadmap/core/services/health/data_integrity_validator_service.py:36: unused class 'DataIntegrityValidatorService'
- roadmap/core/services/health/data_integrity_validator_service.py:45: unused method 'run_all_data_integrity_checks'

Entity Health Scanner:
- roadmap/core/services/health/entity_health_scanner.py:51: unused attribute '_entity_cache'

Health Check Service:
- roadmap/core/services/health/health_check_service.py:17: unused class 'HealthCheckService'
- roadmap/core/services/health/health_check_service.py:64: unused method 'get_check_status'
- roadmap/core/services/health/health_check_service.py:80: unused method 'get_health_summary'
- roadmap/core/services/health/health_check_service.py:144: unused method 'is_unhealthy'

Infrastructure Validator:
- roadmap/core/services/health/infrastructure_validator_service.py:273: unused class 'InfrastructureValidator'
- roadmap/core/services/health/infrastructure_validator_service.py:282: unused method 'run_all_infrastructure_checks'

### Initialization
- roadmap/core/services/initialization/workflow.py:52: unused method 'create_structure'
- roadmap/core/services/initialization_service.py:25: unused class 'ProjectInitializationService'
- roadmap/core/services/initialization_service.py:37: unused method 'validate_prerequisites'
- roadmap/core/services/initialization_service.py:57: unused method 'handle_force_reinitialization'
- roadmap/core/services/initialization_service.py:85: unused method 'validate_finalization'

### Issue Services
Assignee Validation:
- roadmap/core/services/issue/assignee_validation_service.py:28: unused class 'GitHubBackend'
- roadmap/core/services/issue/assignee_validation_service.py:71: unused method 'get_validation_mode'

Issue Filter:
- roadmap/core/services/issue/issue_filter_service.py:294: unused method 'format_time_display'

Issue Matching:
- roadmap/core/services/issue/issue_matching_service.py:27: unused attribute 'local_issues_by_id'
- roadmap/core/services/issue/issue_matching_service.py:71: unused method 'find_matches_batch'

Issue Update:
- roadmap/core/services/issue/issue_update_service.py:13: unused class 'IssueUpdateService'
- roadmap/core/services/issue/issue_update_service.py:118: unused method 'display_update_result'

Start Issue:
- roadmap/core/services/issue/start_issue_service.py:118: unused method 'display_started'

### Issue Helpers
- roadmap/core/services/issue_helpers/issue_filters.py:288: unused method 'format_time_display'

### Project Service
- roadmap/core/services/project/project_status_service.py:26: unused method 'get_project_overview'
- roadmap/core/services/project/project_status_service.py:86: unused method 'get_assignee_workload'
- roadmap/core/services/project/project_status_service.py:105: unused method 'get_status_summary'

### Sync Services
Conflict Resolver:
- roadmap/core/services/sync/conflict_resolver.py:100: unused method 'resolve_issue_conflicts'
- roadmap/core/services/sync/conflict_resolver.py:143: unused method 'has_critical_conflicts'
- roadmap/core/services/sync/conflict_resolver.py:152: unused method 'get_strategy_for_field'

Metadata Service:
- roadmap/core/services/sync/sync_metadata_service.py:154: unused method 'record_sync'
- roadmap/core/services/sync/sync_metadata_service.py:190: unused method 'get_sync_history'

Sync Report:
- roadmap/core/services/sync/sync_report.py:72: unused method 'get_change_description'
- roadmap/core/services/sync/sync_report.py:88: unused method 'is_three_way_conflict'

Sync State:
- roadmap/core/services/sync/sync_state.py:66: unused method 'get_issue_dict'
- roadmap/core/services/sync/sync_state.py:79: unused method 'add_issue'
- roadmap/core/services/sync/sync_state.py:105: unused method 'mark_deleted'
- roadmap/core/services/sync/sync_state.py:118: unused method 'mark_synced'

Sync State Comparator:
- roadmap/core/services/sync/sync_state_comparator.py:111: unused method 'identify_conflicts'
- roadmap/core/services/sync/sync_state_comparator.py:190: unused method 'identify_updates'
- roadmap/core/services/sync/sync_state_comparator.py:262: unused method 'identify_pulls'
- roadmap/core/services/sync/sync_state_comparator.py:333: unused method 'identify_up_to_date'

Sync State Manager:
- roadmap/core/services/sync/sync_state_manager.py:51: unused method 'save_sync_state'
- roadmap/core/services/sync/sync_state_manager.py:238: unused method 'save_base_state'
- roadmap/core/services/sync/sync_state_manager.py:311: unused method 'create_sync_state_from_issues'
- roadmap/core/services/sync/sync_state_manager.py:370: unused method 'migrate_json_to_db'

Three Way Merger:
- roadmap/core/services/sync/three_way_merger.py:32: unused class 'ThreeWayMerger'
- roadmap/core/services/sync/three_way_merger.py:140: unused method 'merge_issues'

### Utility Services
Configuration:
- roadmap/core/services/utils/configuration_service.py:74: unused method 'get_github_token'

Critical Path Calculator:
- roadmap/core/services/utils/critical_path_calculator.py:36: unused variable 'issues_by_criticality'
- roadmap/core/services/utils/critical_path_calculator.py:370: unused method 'find_blocking_issues'
- roadmap/core/services/utils/critical_path_calculator.py:395: unused method 'find_blocked_issues'

Dependency Analyzer:
- roadmap/core/services/utils/dependency_analyzer.py:326: unused method 'get_issues_affecting'

Remote Fetcher:
- roadmap/core/services/utils/remote_fetcher.py:141: unused method 'fetch_issues'

Retry Policy:
- roadmap/core/services/utils/retry_policy.py:40: unused method 'sleep_for_attempt'

### Validators
Milestone Naming:
- roadmap/core/services/validators/milestone_naming_validator.py:29: unused method 'is_valid_name'
- roadmap/core/services/validators/milestone_naming_validator.py:73: unused method 'validate_with_feedback'
- roadmap/core/services/validators/milestone_naming_validator.py:115: unused method 'find_naming_conflicts'

Missing Headlines:
- roadmap/core/services/validators/missing_headlines_validator.py:21: unused method 'check_missing_headlines'

Utility:
- roadmap/core/services/validators/_utils.py:11: unused variable 'total_size_bytes'

### Core Utils
GitHub URLs:
- roadmap/core/utils/github_urls.py:4: unused function 'get_issue_url'
- roadmap/core/utils/github_urls.py:19: unused function 'get_milestone_url'
- roadmap/core/utils/github_urls.py:36: unused function 'get_repo_url'
- roadmap/core/utils/github_urls.py:49: unused function 'parse_github_number'

### Services Init
- roadmap/core/services/__init__.py:125: unused function '__getattr__'

---

## Category: Infrastructure
Coordination and gateway layer

### Coordination
Coordinator Params:
- roadmap/infrastructure/coordination/coordinator_params.py:48: unused class 'MilestoneCreateParams'
- roadmap/infrastructure/coordination/coordinator_params.py:57: unused class 'MilestoneUpdateParams'
- roadmap/infrastructure/coordination/coordinator_params.py:68: unused class 'ProjectCreateParams'
- roadmap/infrastructure/coordination/coordinator_params.py:77: unused class 'ProjectUpdateParams'

Core Coordinator:
- roadmap/infrastructure/coordination/core.py:123: unused attribute 'config_service'
- roadmap/infrastructure/coordination/core.py:174: unused attribute 'validation'
- roadmap/infrastructure/coordination/core.py:180: unused method '_check_initialized'
- roadmap/infrastructure/coordination/core.py:329: unused method 'ensure_database_synced'

Git Coordinator:
- roadmap/infrastructure/coordination/git_coordinator.py:40: unused method 'create_issue_with_branch'
- roadmap/infrastructure/coordination/git_coordinator.py:52: unused method 'update_issue_from_activity'
- roadmap/infrastructure/coordination/git_coordinator.py:102: unused method 'get_local_changes'

Milestone Coordinator:
- roadmap/infrastructure/coordination/milestone_coordinator.py:118: unused method 'validate_naming_consistency'
- roadmap/infrastructure/coordination/milestone_coordinator.py:126: unused method 'fix_naming_consistency'

Project Coordinator:
- roadmap/infrastructure/coordination/project_coordinator.py:104: unused method 'complete'

Team Coordinator:
- roadmap/infrastructure/coordination/team_coordinator.py:35: unused method 'get_members'

User Operations:
- roadmap/infrastructure/coordination/user_operations.py:128: unused method 'legacy_validate_assignee'

### Gateways
Coordination Gateway:
- roadmap/infrastructure/coordination_gateway.py:107: unused method 'parse_issue'
- roadmap/infrastructure/coordination_gateway.py:121: unused method 'parse_milestone'
- roadmap/infrastructure/coordination_gateway.py:135: unused method 'get_yaml_repositories_manager'

Git Gateway:
- roadmap/infrastructure/git_gateway.py:15: unused class 'GitGateway'

GitHub Gateway:
- roadmap/infrastructure/github_gateway.py:43: unused method 'get_github_api_error'

Validation Gateway:
- roadmap/infrastructure/validation_gateway.py:37: unused method 'parse_issue_for_validation'
- roadmap/infrastructure/validation_gateway.py:65: unused method 'get_parser_module'

### Observability
Health:
- roadmap/infrastructure/observability/health.py:36: unused attribute 'directory_checker'
- roadmap/infrastructure/observability/health.py:37: unused attribute 'data_checker'
- roadmap/infrastructure/observability/health.py:38: unused attribute 'entity_checker'

Health Formatter:
- roadmap/infrastructure/observability/health_formatter.py:12: unused method 'summarize_health_checks'
- roadmap/infrastructure/observability/health_formatter.py:43: unused method 'get_status_color'
- roadmap/infrastructure/observability/health_formatter.py:61: unused method 'format_status_display'

### Security
Credentials:
- roadmap/infrastructure/security/credentials.py:97: unused method 'delete_token'
- roadmap/infrastructure/security/credentials.py:127: unused method 'is_available'
- roadmap/infrastructure/security/credentials.py:390: unused function 'mask_token'

### Validation
File Enumeration:
- roadmap/infrastructure/validation/file_enumeration.py:147: unused method 'find_by_id'

---

## Category: Settings & Version
Application configuration

### Settings
- roadmap/settings.py:111: unused function 'get_settings'
- roadmap/settings.py:256: unused function 'get_database_path'
- roadmap/settings.py:267: unused function 'get_log_directory'
- roadmap/settings.py:278: unused function 'is_github_enabled'
- roadmap/settings.py:293: unused function 'get_export_settings'
- roadmap/settings.py:302: unused function 'switch_environment'

### Version
- roadmap/version.py:46: unused method 'bump_major'
- roadmap/version.py:50: unused method 'bump_minor'
- roadmap/version.py:54: unused method 'bump_patch'
- roadmap/version.py:99: unused class 'VersionManager'
- roadmap/version.py:145: unused method 'check_version_consistency'
- roadmap/version.py:181: unused method 'update_version'
- roadmap/version.py:222: unused method 'get_git_status'
- roadmap/version.py:330: unused method 'generate_changelog_entry'
- roadmap/version.py:346: unused method 'update_changelog'

---

## Summary Statistics

- **Total Findings**: 434
- **CLI Commands/Handlers**: ~50 (FALSE_POSITIVE - Click registered)
- **Interface Methods**: ~40 (FALSE_POSITIVE - Protocol definitions)
- **Provider Functions**: ~40 (FALSE_POSITIVE - Dynamically imported)
- **Helper/Utility Methods**: ~100 (REVIEW - Partial usage or legacy)
- **Service Layer Methods**: ~80 (REVIEW - Various integration patterns)
- **Domain Model Methods**: ~30 (REVIEW - Potential model refactoring)
- **Constants/Variables**: ~50 (REVIEW - Config schema declarations)
- **Classes/Presenters**: ~10 (REVIEW - Potential unused implementations)

## Action Plan

### Phase 1: Mark False Positives
1. Add CLI command handlers to `.vultureignore`
2. Add interface/protocol methods to `.vultureignore`
3. Add dynamic provider functions to `.vultureignore`

### Phase 2: Review High-Impact Items
1. GitHub handler methods (likely API surface)
2. Sync orchestration methods (likely refactoring artifacts)
3. Persistence layer (database/storage patterns)

### Phase 3: Decision & Action
1. Categorize remaining items
2. Either delete dead code or add `# noqa: F841` inline comments
3. Document decisions in code
