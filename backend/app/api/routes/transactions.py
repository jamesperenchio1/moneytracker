from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.bank import BankAccount
from app.models.transaction import Transaction, Category
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionListResponse,
    CategoryResponse,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.post("/", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify account belongs to user
    result = await db.execute(
        select(BankAccount)
        .options(selectinload(BankAccount.bank))
        .where(BankAccount.id == data.bank_account_id, BankAccount.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    txn = Transaction(
        bank_account_id=data.bank_account_id,
        transaction_type=data.transaction_type,
        amount=data.amount,
        currency=data.currency,
        description=data.description,
        sender=data.sender,
        receiver=data.receiver,
        reference=data.reference,
        category_id=data.category_id,
        transaction_date=data.transaction_date,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)

    return TransactionResponse(
        id=txn.id,
        bank_account_id=txn.bank_account_id,
        category_id=txn.category_id,
        transaction_type=txn.transaction_type.value,
        amount=float(txn.amount),
        currency=txn.currency,
        description=txn.description,
        sender=txn.sender,
        receiver=txn.receiver,
        bank_name=account.bank.name,
        transaction_date=txn.transaction_date,
        created_at=txn.created_at,
    )


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    bank_account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    # Base query: only user's accounts
    user_accounts = select(BankAccount.id).where(BankAccount.user_id == user.id)
    conditions = [Transaction.bank_account_id.in_(user_accounts)]

    if bank_account_id:
        conditions.append(Transaction.bank_account_id == bank_account_id)
    if category_id:
        conditions.append(Transaction.category_id == category_id)
    if start_date:
        conditions.append(Transaction.transaction_date >= start_date)
    if end_date:
        conditions.append(Transaction.transaction_date <= end_date)

    where_clause = and_(*conditions)

    # Count
    count_result = await db.execute(select(func.count(Transaction.id)).where(where_clause))
    total = count_result.scalar()

    # Fetch with joins
    result = await db.execute(
        select(Transaction)
        .options(
            selectinload(Transaction.category),
            selectinload(Transaction.bank_account).selectinload(BankAccount.bank),
        )
        .where(where_clause)
        .order_by(Transaction.transaction_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    txns = result.scalars().all()

    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                id=t.id,
                bank_account_id=t.bank_account_id,
                category_id=t.category_id,
                category_name=t.category.display_name if t.category else None,
                transaction_type=t.transaction_type.value,
                amount=float(t.amount),
                currency=t.currency,
                description=t.description,
                sender=t.sender,
                receiver=t.receiver,
                bank_name=t.bank_account.bank.name if t.bank_account and t.bank_account.bank else None,
                transaction_date=t.transaction_date,
                created_at=t.created_at,
            )
            for t in txns
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
