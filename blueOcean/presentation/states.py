from dataclasses import dataclass, field

from blueOcean.application.dto import AccountCredentialInfo


@dataclass(frozen=True)
class OhlcvFetchDialogState:
    accout: AccountCredentialInfo = field(default=None)
    symbol: str = field(default="")
    accounts: list[AccountCredentialInfo] = field(default_factory=list)
