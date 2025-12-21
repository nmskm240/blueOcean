from blueOcean.domain.account import Account, AccountId, ApiCredential


def test_create():
    account_id = AccountId.create()

    assert isinstance(account_id.value, str)
    assert account_id.value


def test_values():
    credential = ApiCredential(
        exchange="binance",
        key="key-1",
        secret="secret-1",
        is_sandbox=True,
    )
    account = Account(id=AccountId("acc-1"), credential=credential, label="main")

    assert account.id.value == "acc-1"
    assert account.credential.exchange == "binance"
    assert account.credential.key == "key-1"
    assert account.credential.secret == "secret-1"
    assert account.credential.is_sandbox is True
    assert account.label == "main"
