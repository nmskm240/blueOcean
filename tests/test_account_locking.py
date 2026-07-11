import pytest

from blueOcean.models import AccountId
from blueOcean.metatrader.workers import WorkerStatus
from blueOcean.usecases import AccountWorkerActiveError, ensure_account_is_editable


class ManagerStub:
    def __init__(self, state):
        self.state = state

    def get_status(self, account_id):
        return WorkerStatus(self.state)


@pytest.mark.parametrize("state", ["starting", "running"])
def test_active_worker_locks_account_settings(state):
    with pytest.raises(AccountWorkerActiveError):
        ensure_account_is_editable(ManagerStub(state), AccountId("account-1"))


@pytest.mark.parametrize("state", ["stopped", "error"])
def test_inactive_worker_allows_account_settings(state):
    ensure_account_is_editable(ManagerStub(state), AccountId("account-1"))
