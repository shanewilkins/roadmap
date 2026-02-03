"""Core models for roadmap."""

from pathlib import Path

from roadmap.core.services.sync.sync_state import IssueBaseState, SyncState

# Import from parent models.py (service params and other models)
# Get the parent directory's models.py file
_models_file = Path(__file__).parent.parent / "models.py"
_models_spec = __import__("importlib.util").util.spec_from_file_location(
    "_models_module", _models_file
)
_models_mod = __import__("importlib.util").util.module_from_spec(_models_spec)
_models_spec.loader.exec_module(_models_mod)

# Re-export items from models.py
NOT_PROVIDED = _models_mod.NOT_PROVIDED
IssueCreateServiceParams = _models_mod.IssueCreateServiceParams
IssueUpdateServiceParams = _models_mod.IssueUpdateServiceParams
ProjectCreateServiceParams = _models_mod.ProjectCreateServiceParams
ProjectUpdateServiceParams = _models_mod.ProjectUpdateServiceParams

__all__ = [
    "NOT_PROVIDED",
    "IssueCreateServiceParams",
    "IssueUpdateServiceParams",
    "ProjectCreateServiceParams",
    "ProjectUpdateServiceParams",
    "IssueBaseState",
    "SyncState",
]
