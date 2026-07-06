from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from peewee import IntegrityError

from blueOcean.container import get_injector
from blueOcean.models import AccountId, AccountNotFoundError
from blueOcean.usecases import (
    CreateAccountInput,
    CreateAccountUseCase,
    DeleteAccountUseCase,
    ListAccountsUseCase,
    UpdateAccountInput,
    UpdateAccountUseCase,
)

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parents[2] / "templates")


def get_create_account_usecase() -> CreateAccountUseCase:
    return get_injector().get(CreateAccountUseCase)


def get_list_accounts_usecase() -> ListAccountsUseCase:
    return get_injector().get(ListAccountsUseCase)


def get_update_account_usecase() -> UpdateAccountUseCase:
    return get_injector().get(UpdateAccountUseCase)


def get_delete_account_usecase() -> DeleteAccountUseCase:
    return get_injector().get(DeleteAccountUseCase)


def render_accounts(
    request: Request,
    list_accounts: ListAccountsUseCase,
    *,
    error: str | None = None,
    status_code: int = 200,
):
    return templates.TemplateResponse(
        request=request,
        name="account_settings.html",
        context={"accounts": list_accounts.execute(), "error": error},
        status_code=status_code,
    )


@router.get("/")
async def index():
    return RedirectResponse("/accounts", status_code=303)


@router.get("/accounts", response_class=HTMLResponse)
async def accounts_page(
    request: Request,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
):
    return render_accounts(request, list_accounts)


@router.post("/accounts")
async def account_create(
    request: Request,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
    create_account: Annotated[CreateAccountUseCase, Depends(get_create_account_usecase)],
    name: str = Form(...),
    path: str = Form(...),
    login: str = Form(...),
    password: str = Form(...),
    server: str = Form(...),
    portable: bool = Form(False),
):
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
        return render_accounts(request, list_accounts, error=str(exc), status_code=422)
    except IntegrityError:
        return render_accounts(
            request, list_accounts, error="同じ表示名のアカウントが存在します", status_code=409
        )
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}")
async def account_update(
    request: Request,
    account_id: str,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
    update_account: Annotated[UpdateAccountUseCase, Depends(get_update_account_usecase)],
    name: str = Form(...),
    path: str = Form(...),
    login: str = Form(...),
    password: str = Form(""),
    server: str = Form(...),
    portable: bool = Form(False),
):
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
        return render_accounts(request, list_accounts, error=str(exc), status_code=422)
    except AccountNotFoundError:
        return render_accounts(
            request, list_accounts, error="アカウントが見つかりません", status_code=404
        )
    except IntegrityError:
        return render_accounts(
            request, list_accounts, error="同じ表示名のアカウントが存在します", status_code=409
        )
    return RedirectResponse("/accounts", status_code=303)


@router.post("/accounts/{account_id}/delete")
async def account_delete(
    request: Request,
    account_id: str,
    list_accounts: Annotated[ListAccountsUseCase, Depends(get_list_accounts_usecase)],
    delete_account: Annotated[DeleteAccountUseCase, Depends(get_delete_account_usecase)],
):
    try:
        delete_account.execute(AccountId(account_id))
    except AccountNotFoundError:
        return render_accounts(
            request, list_accounts, error="アカウントが見つかりません", status_code=404
        )
    return RedirectResponse("/accounts", status_code=303)
