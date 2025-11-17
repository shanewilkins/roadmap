"""Configuration management for roadmap CLI application.

This module provides environment-aware configuration using dynaconf,
supporting multiple environments (development, testing, production) and
various configuration sources (files, environment variables, etc.).
"""

from pathlib import Path
from typing import Any

from dynaconf import Dynaconf, Validator

from .logging import get_logger

logger = get_logger(__name__)


def get_config_paths() -> dict[str, Path]:
    """Get standard configuration file paths."""
    home_config_dir = Path.home() / ".roadmap"
    home_config_dir.mkdir(exist_ok=True)

    return {
        "global_config": home_config_dir / "settings.toml",
        "global_secrets": home_config_dir / "secrets.toml",
        "local_config": Path.cwd() / ".roadmap" / "settings.toml",
        "local_secrets": Path.cwd() / ".roadmap" / "secrets.toml",
    }


# Configuration schema with validation
_validators = [
    # Database settings
    Validator("database.path", default="~/.roadmap/roadmap.db"),
    Validator("database.timeout", default=30.0, gte=1.0),
    Validator("database.backup_count", default=5, gte=0),
    # Logging settings
    Validator(
        "logging.level",
        default="INFO",
        is_in=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    ),
    Validator("logging.to_file", default=True, is_type_of=bool),
    Validator("logging.log_dir", default="~/.roadmap/logs"),
    Validator("logging.max_file_size", default="10MB"),
    Validator("logging.backup_count", default=5, gte=0),
    # Git settings
    Validator("git.auto_sync", default=True, is_type_of=bool),
    Validator("git.hooks_enabled", default=True, is_type_of=bool),
    Validator("git.default_branch", default="main"),
    # GitHub integration (optional)
    Validator("github.enabled", default=False, is_type_of=bool),
    Validator("github.token", default=""),
    Validator("github.repo", default=""),
    Validator("github.sync_labels", default=True, is_type_of=bool),
    # CLI settings
    Validator("cli.default_editor", default="nano"),
    Validator("cli.pager", default="less"),
    Validator(
        "cli.output_format", default="table", is_in=["table", "json", "yaml", "csv"]
    ),
    Validator("cli.color", default=True, is_type_of=bool),
    # Project defaults
    Validator("defaults.issue_type", default="task"),
    Validator("defaults.priority", default="medium"),
    Validator("defaults.status", default="open"),
    # Performance settings
    Validator("performance.cache_enabled", default=True, is_type_of=bool),
    Validator("performance.cache_size", default="100MB"),
    Validator("performance.cache_ttl", default=3600, gte=0),
    # Export settings
    Validator(
        "export.default_format", default="csv", is_in=["csv", "json", "yaml", "xlsx"]
    ),
    Validator("export.include_metadata", default=False, is_type_of=bool),
    Validator("export.date_format", default="%Y-%m-%d"),
]

# Initialize dynaconf with our configuration
config_paths = get_config_paths()

settings = Dynaconf(
    # Configuration file locations (in priority order)
    settings_files=[
        str(config_paths["global_config"]),
        str(config_paths["local_config"]),
    ],
    # Secrets file locations
    secrets=[
        str(config_paths["global_secrets"]),
        str(config_paths["local_secrets"]),
    ],
    # Environment variables
    envvar_prefix="ROADMAP",
    # Environment-specific settings
    environments=True,
    env_switcher="ROADMAP_ENV",
    # Validation
    validators=_validators,
    # Additional settings
    load_dotenv=True,
    dotenv_path=".env",
    merge_enabled=True,
    # Default environment
    default_env="development",
)


def get_settings() -> Dynaconf:
    """Get the global settings object."""
    return settings


def validate_config() -> bool:
    """Validate the current configuration."""
    try:
        settings.validators.validate_all()
        logger.info("Configuration validation passed")
        return True
    except Exception as e:
        logger.error("Configuration validation failed", error=str(e))
        return False


def create_default_config(force: bool = False) -> bool:
    """Create default configuration files.

    Args:
        force: Overwrite existing configuration files

    Returns:
        True if configuration was created successfully
    """
    config_paths = get_config_paths()

    # Default global configuration
    global_config_content = """# Roadmap CLI Global Configuration

[default]
# Database settings
[default.database]
path = "~/.roadmap/roadmap.db"
timeout = 30.0
backup_count = 5

# Logging settings
[default.logging]
level = "INFO"
to_file = true
log_dir = "~/.roadmap/logs"
max_file_size = "10MB"
backup_count = 5

# Git settings
[default.git]
auto_sync = true
hooks_enabled = true
default_branch = "main"

# GitHub integration (optional)
[default.github]
enabled = false
sync_labels = true

# CLI settings
[default.cli]
default_editor = "nano"
pager = "less"
output_format = "table"
color = true

# Project defaults
[default.defaults]
issue_type = "task"
priority = "medium"
status = "open"

# Performance settings
[default.performance]
cache_enabled = true
cache_size = "100MB"
cache_ttl = 3600

# Export settings
[default.export]
default_format = "csv"
include_metadata = false
date_format = "%Y-%m-%d"

# Development environment overrides
[development]
[development.logging]
level = "DEBUG"

# Testing environment overrides
[testing]
[testing.database]
path = ":memory:"
[testing.logging]
level = "WARNING"
to_file = false

# Production environment overrides
[production]
[production.logging]
level = "INFO"
[production.performance]
cache_size = "500MB"
"""

    # Default secrets template
    secrets_content = """# Roadmap CLI Secrets Configuration
# Store sensitive information here

[default]
# GitHub token (if using GitHub integration)
[default.github]
token = ""

# Custom API keys or tokens
[default.api_keys]
# example_service = "your-api-key-here"
"""

    try:
        # Create global config if it doesn't exist or force is True
        global_config_path = config_paths["global_config"]
        if not global_config_path.exists() or force:
            global_config_path.write_text(global_config_content)
            logger.info("Created global configuration", path=str(global_config_path))

        # Create secrets template if it doesn't exist or force is True
        global_secrets_path = config_paths["global_secrets"]
        if not global_secrets_path.exists() or force:
            global_secrets_path.write_text(secrets_content)
            global_secrets_path.chmod(0o600)  # Secure permissions
            logger.info("Created secrets configuration", path=str(global_secrets_path))

        return True

    except Exception as e:
        logger.error("Failed to create default configuration", error=str(e))
        return False


def get_database_path() -> Path:
    """Get the configured database path."""
    db_path = settings.database.path
    if db_path.startswith("~"):
        db_path = Path(db_path).expanduser()
    else:
        db_path = Path(db_path)

    return db_path


def get_log_directory() -> Path:
    """Get the configured log directory."""
    log_dir = settings.logging.log_dir
    if log_dir.startswith("~"):
        log_dir = Path(log_dir).expanduser()
    else:
        log_dir = Path(log_dir)

    return log_dir


def is_github_enabled() -> bool:
    """Check if GitHub integration is enabled."""
    return settings.github.enabled and bool(settings.github.token)


def get_github_config() -> dict[str, Any]:
    """Get GitHub configuration."""
    return {
        "enabled": settings.github.enabled,
        "token": settings.github.token,
        "repo": settings.github.repo,
        "sync_labels": settings.github.sync_labels,
    }


def get_export_settings() -> dict[str, Any]:
    """Get export settings."""
    return {
        "default_format": settings.export.default_format,
        "include_metadata": settings.export.include_metadata,
        "date_format": settings.export.date_format,
    }


def switch_environment(env_name: str) -> bool:
    """Switch to a different environment.

    Args:
        env_name: Environment name (development, testing, production)

    Returns:
        True if environment was switched successfully
    """
    try:
        import os

        os.environ["ROADMAP_ENV"] = env_name
        settings.setenv(env_name)
        logger.info("Switched environment", environment=env_name)
        return True
    except Exception as e:
        logger.error("Failed to switch environment", environment=env_name, error=str(e))
        return False


# Initialize default configuration on module import
try:
    validate_config()
    logger.debug("Configuration loaded successfully")
except Exception as e:
    logger.warning("Configuration validation failed, creating defaults", error=str(e))
    create_default_config()
