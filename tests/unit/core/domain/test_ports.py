"""Unit tests for core domain port interfaces."""

import pytest

from roadmap.common.result import Ok
from roadmap.core.domain.ports.baseline_repository import IBaselineRepository
from roadmap.core.domain.ports.remote_backend_port import IRemoteBackendPort
from roadmap.core.services.sync.sync_state import SyncState


class _ConcreteBaselineRepo(IBaselineRepository):
    def load(self):  # noqa: ANN201
        return None

    def save(self, baseline):  # noqa: ANN001, ANN201
        self.last_saved = baseline

    def clear(self):
        self.last_saved = None


class _ConcreteRemoteBackend(IRemoteBackendPort):
    def authenticate(self):
        return Ok(None)

    def get_issues(self):
        return Ok({})

    def push_issue(self, issue_id, _payload):  # noqa: ANN001, ARG002
        return Ok(None)

    def pull_issue(self, remote_id):  # noqa: ANN001, ARG002
        return Ok(
            {
                "id": "placeholder",
            }
        )


@pytest.mark.parametrize("abstract_cls", [IBaselineRepository, IRemoteBackendPort])
def test_abstract_ports_cannot_be_instantiated(abstract_cls):
    """ABC interfaces should not be directly instantiable."""
    with pytest.raises(TypeError):
        abstract_cls()  # type: ignore[misc]


def test_concrete_baseline_repo_implements_interface():
    """Concrete baseline implementation should satisfy interface methods."""
    repo = _ConcreteBaselineRepo()
    baseline = SyncState()
    repo.save(baseline)
    assert repo.load() is None
    assert repo.last_saved is baseline
    repo.clear()
    assert repo.last_saved is None


def test_concrete_remote_backend_returns_result_objects():
    """Concrete remote backend implementation should return Result values."""
    backend = _ConcreteRemoteBackend()

    assert backend.authenticate().is_ok()
    assert backend.get_issues().is_ok()
    assert backend.push_issue("id-1", {}).is_ok()
    assert backend.pull_issue("remote-id").is_ok()
