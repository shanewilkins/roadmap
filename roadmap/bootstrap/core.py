"""Construction of the retained collaborator graph."""

from pathlib import Path

from roadmap.adapters.inbound.cli import WorkspaceServices
from roadmap.adapters.outbound.git import SubprocessLocalGit
from roadmap.adapters.outbound.persistence import (
    CanonicalIssueUnitOfWorkFactory,
    DocumentIssueQueries,
    FilesystemWorkspaceDiagnostics,
)
from roadmap.adapters.outbound.persistence.configuration import ConfigurationFiles
from roadmap.adapters.outbound.persistence.documents import DocumentRepository
from roadmap.adapters.outbound.persistence.initialization import (
    FilesystemWorkspaceLayout,
)
from roadmap.adapters.outbound.persistence.projection import SQLiteProjection
from roadmap.adapters.outbound.system import (
    ConfiguredCurrentIdentity,
    LocalAssigneeDirectory,
    SystemClock,
)
from roadmap.application.use_cases import (
    IssueMutations,
    IssueQueries,
    LocalGit,
    Planning,
    WorkspaceHealth,
    WorkspaceInitialization,
)


def _planning(roadmap_dir: Path, clock: SystemClock) -> Planning:
    documents = DocumentRepository(roadmap_dir)
    projection = SQLiteProjection(roadmap_dir / "db" / "projection.db", documents)
    return Planning(CanonicalIssueUnitOfWorkFactory(documents, projection), clock)


def create_initialization(
    root_path: Path, roadmap_dir_name: str = ".roadmap"
) -> WorkspaceInitialization:
    """Construct initialization against an explicit local directory."""
    roadmap_dir = root_path / roadmap_dir_name
    return WorkspaceInitialization(
        FilesystemWorkspaceLayout(root_path, roadmap_dir_name),
        _planning(roadmap_dir, SystemClock()),
    )


def create_core(
    root_path: Path, roadmap_dir_name: str = ".roadmap"
) -> WorkspaceServices:
    """Construct command-facing services through the sole composition root."""
    roadmap_dir = root_path / roadmap_dir_name
    documents = DocumentRepository(roadmap_dir)
    projection = SQLiteProjection(roadmap_dir / "db" / "projection.db", documents)
    units = CanonicalIssueUnitOfWorkFactory(documents, projection)
    clock = SystemClock()
    configuration = ConfigurationFiles(
        roadmap_dir / "config.yaml",
        Path.home() / ".config" / "roadmap" / "config.yaml",
    )
    resolved = configuration.resolve()
    local_git_adapter = SubprocessLocalGit(root_path)
    identity = ConfiguredCurrentIdentity(resolved.user.name, local_git_adapter)
    queries = IssueQueries(DocumentIssueQueries(documents, projection), identity, clock)
    mutations = IssueMutations(units, identity, LocalAssigneeDirectory(), clock)
    return WorkspaceServices(
        root_path,
        roadmap_dir,
        configuration,
        identity,
        queries,
        mutations,
        LocalGit(local_git_adapter, queries, mutations),
        Planning(units, clock),
        WorkspaceHealth(FilesystemWorkspaceDiagnostics(documents, projection)),
    )


def find_existing_core(root_path: Path | None = None) -> WorkspaceServices | None:
    """Find the nearest initialized canonical workspace."""
    start = (root_path or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / ".roadmap" / "config.yaml").is_file():
            return create_core(candidate)
    return None
