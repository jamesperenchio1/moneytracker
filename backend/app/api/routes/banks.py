from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.bank import Bank, BankAccount
from app.schemas.bank import BankAccountCreate, BankAccountResponse, BankResponse

router = APIRouter(prefix="/banks", tags=["banks"])


@router.get("", response_model=list[BankResponse])
async def list_banks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bank).order_by(Bank.name))
    return result.scalars().all()


@router.post("/accounts", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    data: BankAccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bank = await db.get(Bank, data.bank_id)
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    account = BankAccount(
        user_id=user.id,
        bank_id=data.bank_id,
        account_number=data.account_number,
        account_name=data.account_name,
        currency=data.currency,
    )
    db.add(account)
    await db.flush()
    await db.refresh(account)

    return BankAccountResponse(
        id=account.id,
        bank_id=account.bank_id,
        bank_name=bank.name,
        bank_code=bank.code.value,
        account_number=account.account_number,
        account_name=account.account_name,
        balance=float(account.balance),
        currency=account.currency,
        created_at=account.created_at,
    )


@router.get("/accounts", response_model=list[BankAccountResponse])
async def list_bank_accounts(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BankAccount)
        .options(selectinload(BankAccount.bank))
        .where(BankAccount.user_id == user.id)
        .order_by(BankAccount.created_at)
    )
    accounts = result.scalars().all()
    return [
        BankAccountResponse(
            id=a.id,
            bank_id=a.bank_id,
            bank_name=a.bank.name,
            bank_code=a.bank.code.value,
            account_number=a.account_number,
            account_name=a.account_name,
            balance=float(a.balance),
            currency=a.currency,
            created_at=a.created_at,
        )
        for a in accounts
    ]


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bank_account(
    account_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id, BankAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
