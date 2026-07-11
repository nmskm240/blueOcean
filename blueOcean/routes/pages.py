from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from peewee import IntegrityError

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

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parents[2] / "templates")


def select_mt5_terminal_path() -> str:
    """Show a native Windows picker and return the selected MT5 executable."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return filedialog.askopenfilename(
            parent=root,
            title="MT5ターミナルを選択",
            filetypes=[
                ("MT5 terminal", "terminal64.exe"),
                ("Executable files", "*.exe"),
                ("All files", "*.*"),
            ],
        )
    finally:
        root.destroy()


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


def render_accounts(
    request: Request,
    list_accounts: ListAccountsUseCase,
    *,
    error: str | None = None,
    status_code: int = 200,
    worker_manager: MT5WorkerManager | None = None,
):
    worker_manager = worker_manager or get_mt5_worker_manager()
    return templates.TemplateResponse(
        request=request,
        name="account_settings.html",
        context={
            "accounts": list_accounts.execute(),
            "error": error,
            "worker_statuses": worker_manager.get_statuses(),
        },
        status_code=status_code,
    )


def render_account_form(
    request: Request,
    *,
    account=None,
    form: dict | None = None,
    error: str | None = None,
    status_code: int = 200,
    locked: bool = False,
):
    if form is None and account is not None:
        form = {
            "name": account.name,
            "path": account.connection.path,
            "login": account.connection.login,
            "server": account.connection.server,
            "portable": account.portable,
        }
    return templates.TemplateResponse(
        request=request,
        name="account_form.html",
        context={
            "account": account,
            "form": form or {},
            "error": error,
            "is_edit": account is not None,
            "locked": locked,
        },
        status_code=status_code,
    )


@router.get("/")
async def index():
    return RedirectResponse("/accounts", status_code=303)


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(
    request: Request,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
    worker_manager: Annotated[MT5WorkerManager, Depends(get_mt5_worker_manager)],
):
    return render_accounts(request, list_accounts, worker_manager=worker_manager)


@router.get("/accounts/new", response_class=HTMLResponse)
async def account_new_page(request: Request):
    return render_account_form(request)


@router.get("/dialogs/mt5-terminal")
def mt5_terminal_dialog():
    try:
        path = select_mt5_terminal_path()
    except Exception as exc:
        return JSONResponse({"detail": f"ファイル選択画面を開けませんでした: {exc}"}, status_code=500)
    return {"path": path}


@router.get("/accounts/worker-statuses")
def account_worker_statuses(
    worker_manager: Annotated[MT5WorkerManager, Depends(get_mt5_worker_manager)],
):
    return {
        account_id: {
            "state": status.state,
            "pid": status.pid,
            "error": status.error,
        }
        for account_id, status in worker_manager.get_statuses().items()
    }


@router.get("/accounts/{account_id}", response_class=HTMLResponse)
async def account_edit_page(
    request: Request,
    account_id: str,
    get_account: Annotated[GetAccountUseCase, Depends(get_account_usecase)],
    worker_manager: Annotated[MT5WorkerManager, Depends(get_mt5_worker_manager)],
):
    try:
        account = get_account.execute(AccountId(account_id))
    except AccountNotFoundError:
        return render_account_form(request, error="アカウントが見つかりません", status_code=404)
    locked = worker_manager.get_status(account_id).state in ("starting", "running")
    return render_account_form(request, account=account, locked=locked)


@router.post("/accounts/{account_id}/start")
async def account_worker_start(
    request: Request,
    account_id: str,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
    start_worker: Annotated[StartMT5WorkerUseCase, Depends(get_start_mt5_worker_usecase)],
):
    try:
        start_worker.execute(AccountId(account_id))
    except AccountNotFoundError:
        return render_accounts(request, list_accounts, error="Account not found", status_code=404)
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}/stop")
async def account_worker_stop(
    account_id: str,
    stop_worker: Annotated[StopMT5WorkerUseCase, Depends(get_stop_mt5_worker_usecase)],
):
    stop_worker.execute(AccountId(account_id))
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts")
async def account_create(
    request: Request,
    create_account: Annotated[CreateAccountUseCase, Depends(get_create_account_usecase)],
    name: str = Form(...),
    path: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    server: str = Form(...),
    portable: bool = Form(False),
):
    form = {"name": name, "path": path, "login": login, "server": server, "portable": portable}
    try:
        create_account.execute(
            CreateAccountInput(
                name=name,
                path=path,
                login=int(login),
                password=password,
                server=server,
                portable=portable,
            )
        )
    except ValueError as exc:
        return render_account_form(request, form=form, error=str(exc), status_code=422)
    except IntegrityError:
        return render_account_form(request, form=form, error="同じ表示名のアカウントが存在します", status_code=409)
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}")
async def account_update(
    request: Request,
    account_id: str,
    get_account: Annotated[GetAccountUseCase, Depends(get_account_usecase)],
    update_account: Annotated[UpdateAccountUseCase, Depends(get_update_account_usecase)],
    name: str = Form(...),
    path: str = Form(...),
    login: str = Form(...),
    password: str = Form(""),
    server: str = Form(...),
    portable: bool = Form(False),
):
    form = {"name": name, "path": path, "login": login, "server": server, "portable": portable}
    try:
        account = get_account.execute(AccountId(account_id))
    except AccountNotFoundError:
        return render_account_form(request, error="アカウントが見つかりません", status_code=404)
    try:
        update_account.execute(
            UpdateAccountInput(
                account_id=AccountId(account_id),
                name=name,
                path=path,
                login=int(login),
                password=password or None,
                server=server,
                portable=portable,
            )
        )
    except ValueError as exc:
        return render_account_form(request, account=account, form=form, error=str(exc), status_code=422)
    except AccountWorkerActiveError as exc:
        return render_account_form(
            request, account=account, form=form, error=str(exc), status_code=409, locked=True
        )
    except AccountNotFoundError:
        return render_account_form(request, form=form, error="アカウントが見つかりません", status_code=404)
    except IntegrityError:
        return render_account_form(request, account=account, form=form, error="同じ表示名のアカウントが存在します", status_code=409)
    return RedirectResponse(f"/accounts/{account_id}", status_code=303)


@router.post("/accounts/{account_id}/delete")
async def account_delete(
    request: Request,
    account_id: str,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
    delete_account: Annotated[DeleteAccountUseCase, Depends(get_delete_account_usecase)],
):
    try:
        delete_account.execute(AccountId(account_id))
    except AccountWorkerActiveError as exc:
        return render_accounts(request, list_accounts, error=str(exc), status_code=409)
    except AccountNotFoundError:
        return render_accounts(
            request, list_accounts, error="アカウントが見つかりません", status_code=404
        )
    return RedirectResponse("/accounts", status_code=303)
