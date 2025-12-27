from typing import overload

from blueOcean.application.dto import AccountCredentialInfo
from blueOcean.domain.account import Account, AccountId, ApiCredential


@overload
def to_account(info: AccountCredentialInfo) -> Account: ...


def to_account(*args):
    match args:
        case (AccountCredentialInfo() as info,) if len(args) == 1:
            return Account(
                id=AccountId(info.account_id),
                credential=ApiCredential(
                    exchange=info.exchange_name,
                    key=info.api_key,
                    secret=info.api_secret,
                    is_sandbox=info.is_sandbox,
                ),
                label=info.label,
            )
        case _:
            raise TypeError("to_account received unsupported arguments")
