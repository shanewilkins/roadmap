"""
Identity management system for roadmap assignee resolution.

This module provides a comprehensive solution for managing user identities
and assignee resolution across different project contexts:

1. Git-integrated projects: Uses GitHub usernames as canonical identifiers
2. Local projects: Uses configurable user profiles with alias resolution
3. Hybrid projects: Combines both approaches with identity learning

Key Features:
- Canonical identity resolution (shane/Shane/Shane Wilkins -> shanewilkins)
- Configurable validation modes (strict/relaxed/github-only/local-only)
- Identity learning and suggestion system
- Git integration for automatic identity discovery
- Team management with role-based permissions
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import yaml

from .file_utils import ensure_directory_exists, file_exists_check

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """Represents a canonical user identity with all known aliases."""

    canonical_id: str  # Primary identifier (e.g., "shane.wilkins" or "shanewilkins")
    display_name: str  # Human-readable name (e.g., "Shane Wilkins")
    email: str | None = None  # Primary email
    github_username: str | None = None  # GitHub username if applicable
    aliases: set[str] = field(default_factory=set)  # All known name variants
    roles: set[str] = field(
        default_factory=set
    )  # project roles (admin, developer, reviewer)
    active: bool = True  # Whether user is active on project
    last_activity: datetime | None = None

    def matches(self, name: str) -> bool:
        """Check if a name matches this user profile."""
        if not name:
            return False

        name_normalized = name.strip().lower()

        # Check exact matches (case-insensitive)
        if (
            name_normalized == self.canonical_id.lower()
            or name_normalized == self.display_name.lower()
            or (self.email and name_normalized == self.email.lower())
            or (
                self.github_username and name_normalized == self.github_username.lower()
            )
        ):
            return True

        # Check aliases
        return any(name_normalized == alias.lower() for alias in self.aliases)

    def add_alias(self, alias: str):
        """Add a new alias for this user."""
        if alias and alias.strip():
            self.aliases.add(alias.strip())


@dataclass
class TeamConfig:
    """Team configuration settings."""

    validation_mode: str = "hybrid"  # strict, relaxed, github-only, local-only, hybrid
    auto_normalize_assignees: bool = True
    require_team_membership: bool = True
    allow_identity_learning: bool = True
    github_org: str | None = None


class IdentityManager:
    """Manages user identities and assignee resolution."""

    def __init__(self, roadmap_path: Path):
        self.roadmap_path = roadmap_path
        self.team_config_path = roadmap_path / ".roadmap" / "team.yaml"
        self.profiles: dict[str, UserProfile] = {}
        self.config = TeamConfig()
        self._load_team_config()

    def _load_team_config(self):
        """Load team configuration and user profiles."""
        if not file_exists_check(self.team_config_path):
            return

        try:
            with open(self.team_config_path) as f:
                data = yaml.safe_load(f) or {}

            # Load configuration
            config_data = data.get("config", {})
            self.config = TeamConfig(**config_data)

            # Load user profiles
            members_data = data.get("team_members", {})
            for canonical_id, member_data in members_data.items():
                profile = UserProfile(
                    canonical_id=canonical_id,
                    display_name=member_data.get("display_name", canonical_id),
                    email=member_data.get("email"),
                    github_username=member_data.get("github_username"),
                    aliases=set(member_data.get("aliases", [])),
                    roles=set(member_data.get("roles", [])),
                    active=member_data.get("active", True),
                )
                self.profiles[canonical_id] = profile

        except Exception as e:
            logger.warning(f"Failed to load team config: {e}")

    def save_team_config(self):
        """Save current team configuration and profiles."""
        # Ensure directory exists
        ensure_directory_exists(self.team_config_path.parent)

        # Prepare data for serialization
        data = {
            "config": {
                "validation_mode": self.config.validation_mode,
                "auto_normalize_assignees": self.config.auto_normalize_assignees,
                "require_team_membership": self.config.require_team_membership,
                "allow_identity_learning": self.config.allow_identity_learning,
                "github_org": self.config.github_org,
            },
            "team_members": {},
        }

        for canonical_id, profile in self.profiles.items():
            data["team_members"][canonical_id] = {
                "display_name": profile.display_name,
                "email": profile.email,
                "github_username": profile.github_username,
                "aliases": list(profile.aliases),
                "roles": list(profile.roles),
                "active": profile.active,
            }

        with open(self.team_config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=True)

    def resolve_assignee(self, name: str) -> tuple[bool, str, UserProfile | None]:
        """
        Resolve an assignee name to a canonical user profile.

        Returns:
            (is_valid, canonical_id_or_error, user_profile)
        """
        if not name or not name.strip():
            return False, "Assignee cannot be empty", None

        name = name.strip()

        # Try to find exact profile match
        for profile in self.profiles.values():
            if profile.matches(name):
                if not profile.active:
                    return (
                        False,
                        f"User '{profile.display_name}' is no longer active on this project",
                        None,
                    )
                return True, profile.canonical_id, profile

        # Handle different validation modes
        if self.config.validation_mode == "strict":
            return self._strict_validation(name)
        elif self.config.validation_mode == "relaxed":
            return self._relaxed_validation(name)
        elif self.config.validation_mode == "github-only":
            return self._github_validation(name)
        elif self.config.validation_mode == "local-only":
            return self._local_validation(name)
        elif self.config.validation_mode == "hybrid":
            return self._hybrid_validation(name)
        else:
            return (
                False,
                f"Unknown validation mode: {self.config.validation_mode}",
                None,
            )

    def _strict_validation(self, name: str) -> tuple[bool, str, UserProfile | None]:
        """Strict mode: Only allow known team members."""
        return (
            False,
            f"Unknown team member '{name}'. Add them to team configuration first.",
            None,
        )

    def _relaxed_validation(self, name: str) -> tuple[bool, str, UserProfile | None]:
        """Relaxed mode: Allow unknown users but suggest similar names."""
        suggestions = self._find_similar_names(name)
        if suggestions:
            suggestion_text = ", ".join(suggestions[:3])
            return (
                False,
                f"Unknown user '{name}'. Did you mean: {suggestion_text}?",
                None,
            )

        # If identity learning is enabled, create a temporary profile
        if self.config.allow_identity_learning:
            return True, name, None  # Allow but don't create profile yet

        return (
            False,
            f"Unknown user '{name}'. Use 'roadmap team add' to add new members.",
            None,
        )

    def _github_validation(self, name: str) -> tuple[bool, str, UserProfile | None]:
        """GitHub mode: Validate against GitHub API."""
        # This would integrate with existing GitHub validation
        # For now, return success if it looks like a GitHub username
        if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-])*[a-zA-Z0-9]$", name):
            return True, name, None
        return False, f"'{name}' does not appear to be a valid GitHub username", None

    def _local_validation(self, name: str) -> tuple[bool, str, UserProfile | None]:
        """Local mode: Accept any reasonable name."""
        if len(name) >= 2 and not any(char in name for char in "<>{}[]()"):
            return True, name, None
        return False, f"'{name}' is not a valid assignee name", None

    def _hybrid_validation(self, name: str) -> tuple[bool, str, UserProfile | None]:
        """Hybrid mode: Try team profiles first, then GitHub, fall back to local."""
        # First try as known team member
        for profile in self.profiles.values():
            if profile.matches(name):
                return True, profile.canonical_id, profile

        # If we have team profiles configured but no match, be more strict
        if self.profiles:
            # Try GitHub validation if it looks like a username
            if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-])*[a-zA-Z0-9]$", name):
                # Return as unresolved to let core.py handle GitHub validation
                return (
                    False,
                    f"Unknown team member '{name}'. Use GitHub validation or add to team.",
                    None,
                )
            else:
                return (
                    False,
                    f"Unknown team member '{name}'. Add them to team configuration first.",
                    None,
                )

        # No team profiles configured - allow reasonable names (for initial setup)
        if re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-])*[a-zA-Z0-9]$", name):
            # Looks like a GitHub username - let core.py handle GitHub validation
            return (
                False,
                "No team configuration found. Falling back to GitHub validation.",
                None,
            )

        # Fall back to local validation for non-GitHub-like names
        return self._local_validation(name)

    def _find_similar_names(self, name: str) -> list[str]:
        """Find similar names in existing profiles using fuzzy matching."""
        similarities = []

        for profile in self.profiles.values():
            # Check against display name and aliases
            candidates = [profile.display_name] + list(profile.aliases)
            if profile.github_username:
                candidates.append(profile.github_username)

            for candidate in candidates:
                ratio = SequenceMatcher(None, name.lower(), candidate.lower()).ratio()
                if ratio > 0.6:  # 60% similarity threshold
                    similarities.append((ratio, candidate))

        # Sort by similarity and return top matches
        similarities.sort(reverse=True)
        return [name for _, name in similarities]

    def add_team_member(
        self,
        canonical_id: str,
        display_name: str,
        github_username: str | None = None,
        email: str | None = None,
        aliases: list[str] | None = None,
    ) -> UserProfile:
        """Add a new team member."""
        profile = UserProfile(
            canonical_id=canonical_id,
            display_name=display_name,
            email=email,
            github_username=github_username,
            aliases=set(aliases or []),
        )

        self.profiles[canonical_id] = profile
        return profile

    def suggest_identity_mappings(
        self, assignee_names: list[str]
    ) -> dict[str, list[str]]:
        """Analyze assignee names and suggest identity clusters."""
        clusters = {}

        # Group similar names
        for name in assignee_names:
            added_to_cluster = False

            for cluster_key, cluster_names in clusters.items():
                # Check if this name is similar to any in the cluster
                for cluster_name in cluster_names:
                    if self._names_likely_same_person(name, cluster_name):
                        clusters[cluster_key].append(name)
                        added_to_cluster = True
                        break

                if added_to_cluster:
                    break

            if not added_to_cluster:
                clusters[name] = [name]

        # Filter out single-item clusters
        return {k: v for k, v in clusters.items() if len(v) > 1}

    def _names_likely_same_person(self, name1: str, name2: str) -> bool:
        """Heuristic to determine if two names likely refer to the same person."""
        name1, name2 = name1.lower(), name2.lower()

        # Exact match
        if name1 == name2:
            return True

        # One is contained in the other (shane vs shane.wilkins)
        if name1 in name2 or name2 in name1:
            return True

        # Email variations (shane@company.com vs shane)
        if "@" in name1 or "@" in name2:
            email_user = name1.split("@")[0] if "@" in name1 else name2.split("@")[0]
            other_name = name2 if "@" in name1 else name1
            if email_user == other_name:
                return True

        # Name components (shane vs shane.wilkins vs Shane Wilkins)
        components1 = re.split(r"[.\s_-]+", name1)
        components2 = re.split(r"[.\s_-]+", name2)

        # Check if all components of shorter name are in longer name
        shorter, longer = (
            (components1, components2)
            if len(components1) <= len(components2)
            else (components2, components1)
        )
        if all(comp in longer for comp in shorter):
            return True

        # Check for initial matches (j.doe vs John Doe)
        # If shorter has single letters that could be initials of longer
        if len(shorter) == len(longer):
            matches = 0
            for s_comp, l_comp in zip(shorter, longer, strict=False):
                if len(s_comp) == 1 and l_comp.startswith(s_comp):
                    matches += 1
                elif s_comp == l_comp:
                    matches += 1
            # If most components match (allowing for initials), likely same person
            if matches >= len(shorter) * 0.7:  # 70% match threshold
                return True

        return False

    def get_user_dashboard_context(self, current_user: str) -> dict[str, Any]:
        """Get context for user dashboard, resolving identity."""
        resolved = self.resolve_assignee(current_user)
        if resolved[0] and resolved[2]:  # Valid with profile
            profile = resolved[2]
            return {
                "canonical_id": profile.canonical_id,
                "display_name": profile.display_name,
                "aliases": list(profile.aliases),
                "github_username": profile.github_username,
                "roles": list(profile.roles),
            }
        else:
            return {
                "canonical_id": current_user,
                "display_name": current_user,
                "aliases": [],
                "github_username": None,
                "roles": [],
            }
