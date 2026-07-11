from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, SecretStr

from blueOcean.container import get_injector
from blueOcean.models import AccountId, AccountNotFoundError
from blueOcean.metatrader.workers import MT5WorkerManager
from blueOcean.usecases import (
    AccountWorkerActiveError,
    CreateAccountInput,
    CreateAccountUseCase,
    DeleteAccountUseCase,
    GetAccountUseCase,
    ListAccountsUseCase,
    StartMT5WorkerUseCase,
    StopMT5WorkerUseCase,
    UpdateAccountInput,
    UpdateAccountUseCase,
)

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


def get_create_account_usecase() -> CreateAccountUseCase:
    return get_injector().get(CreateAccountUseCase)


def get_list_accounts_usecase() -> ListAccountsUseCase:
    return get_injector().get(ListAccountsUseCase)


def get_account_usecase() -> GetAccountUseCase:
    return get_injector().get(GetAccountUseCase)


def get_update_account_usecase() -> UpdateAccountUseCase:
    return get_injector().get(UpdateAccountUseCase)


def get_delete_account_usecase() -> DeleteAccountUseCase:
    return get_injector().get(DeleteAccountUseCase)


def get_start_mt5_worker_usecase() -> StartMT5WorkerUseCase:
    return get_injector().get(StartMT5WorkerUseCase)


def get_stop_mt5_worker_usecase() -> StopMT5WorkerUseCase:
    return get_injector().get(StopMT5WorkerUseCase)


def get_mt5_worker_manager() -> MT5WorkerManager:
    return get_injector().get(MT5WorkerManager)


class AccountInput(BaseModel):
    name: str
    path: str = ""
    login: int | None = None
    server: str = ""
    portable: bool = False


class AccountCreate(AccountInput):
    password: SecretStr


class AccountUpdate(AccountInput):
    password: SecretStr | None = None


class AccountOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    path: str
    login: int | None
    server: str
    portable: bool
    has_password: bool


class WorkerOutput(BaseModel):
    state: str
    pid: int | None = None
    error: str | None = None


@router.get("", response_model=list[AccountOutput])
async def list_accounts(
    usecase: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
):
    return [_account_output(account) for account in usecase.execute()]


@router.get("/{account_id}", response_model=AccountOutput)
async def get_account(
    account_id: str,
    usecase: Annotated[GetAccountUseCase, Depends(get_account_usecase)],
):
    try:
        return _account_output(usecase.execute(AccountId(account_id)))
    except AccountNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")


@router.get("/{account_id}/worker", response_model=WorkerOutput)
async def get_account_worker(
    account_id: str,
    get_account: Annotated[GetAccountUseCase, Depends(get_account_usecase)],
    manager: Annotated[MT5WorkerManager, Depends(get_mt5_worker_manager)],
):
    try:
        get_account.execute(AccountId(account_id))
    except AccountNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")
    return manager.get_status(account_id)


@router.post("/{account_id}/worker/start", response_model=WorkerOutput, status_code=202)
async def start_account_worker(
    account_id: str,
    usecase: Annotated[StartMT5WorkerUseCase, Depends(get_start_mt5_worker_usecase)],
):
    try:
        return usecase.execute(AccountId(account_id))
    except AccountNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{account_id}/worker/stop", response_model=WorkerOutput)
async def stop_account_worker(
    account_id: str,
    get_account: Annotated[GetAccountUseCase, Depends(get_account_usecase)],
    usecase: Annotated[StopMT5WorkerUseCase, Depends(get_stop_mt5_worker_usecase)],
):
    try:
        get_account.execute(AccountId(account_id))
    except AccountNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")
    return usecase.execute(AccountId(account_id))


@router.post("", response_model=AccountOutput, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    usecase: Annotated[CreateAccountUseCase, Depends(get_create_account_usecase)],
):
    try:
        account = usecase.execute(
            CreateAccountInput(
                name=payload.name,
                path=payload.path,
                login=payload.login,
                password=payload.password.get_secret_value(),
                server=payload.server,
                portable=payload.portable,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _account_output(account)


@router.put("/{account_id}", response_model=AccountOutput)
async def update_account(
    account_id: str,
    payload: AccountUpdate,
    usecase: Annotated[UpdateAccountUseCase, Depends(get_update_account_usecase)],
):
    try:
        account = usecase.execute(
            UpdateAccountInput(
                account_id=AccountId(account_id),
                name=payload.name,
                path=payload.path,
                login=payload.login,
                password=payload.password.get_secret_value() if payload.password else None,
                server=payload.server,
                portable=payload.portable,
            )
        )
    except AccountNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")
    except AccountWorkerActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _account_output(account)


@router.delete("/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    usecase: Annotated[DeleteAccountUseCase, Depends(get_delete_account_usecase)],
) -> Response:
    try:
        usecase.execute(AccountId(account_id))
    except AccountNotFoundError:
        raise HTTPException(status_code=404, detail="Account not found")
    except AccountWorkerActiveError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return Response(status_code=204)


def _account_output(account) -> AccountOutput:
    return AccountOutput(
        id=account.id.value,
        name=account.name,
        path=account.connection.path,
        login=account.connection.login,
        server=account.connection.server,
        portable=account.portable,
        has_password=account.has_password,
    )
