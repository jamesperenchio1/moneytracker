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
from app.models.statement import Statement
from app.models.transaction import Transaction, Category, CategoryName
from app.services.categorizer import infer_category, suggest_categories
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    CategoryResponse,
    CategorySuggestion,
    CategorySuggestionRequest,
    CategorySuggestionResponse,
    RecategorizeResponse,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _txn_to_response(t: Transaction) -> TransactionResponse:
    """Convert a Transaction ORM object to TransactionResponse."""
    return TransactionResponse(
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
        reference=t.reference,
        bank_name=t.bank_account.bank.name if t.bank_account and t.bank_account.bank else None,
        statement_file_name=t.statement.file_name if t.statement else None,
        transaction_date=t.transaction_date,
        created_at=t.created_at,
    )


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    return result.scalars().all()


@router.post("", response_model=TransactionResponse, status_code=201)
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


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a transaction's category."""
    # Fetch transaction with related data
    user_accounts = select(BankAccount.id).where(BankAccount.user_id == user.id)
    result = await db.execute(
        select(Transaction)
        .options(
            selectinload(Transaction.category),
            selectinload(Transaction.bank_account).selectinload(BankAccount.bank),
            selectinload(Transaction.statement),
        )
        .where(
            Transaction.id == transaction_id,
            Transaction.bank_account_id.in_(user_accounts),
        )
    )
    txn = result.scalar_one_or_none()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Verify category exists
    cat_result = await db.execute(select(Category).where(Category.id == data.category_id))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    txn.category_id = data.category_id
    txn.category = category
    await db.commit()
    await db.refresh(txn)

    return _txn_to_response(txn)


@router.post("/suggest-category", response_model=CategorySuggestionResponse)
async def suggest_category(
    data: CategorySuggestionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get category suggestions for a description string."""
    suggestions = suggest_categories(data.description)

    # Load category display names
    cat_result = await db.execute(select(Category))
    categories = {c.name.value: c for c in cat_result.scalars().all()}

    result = []
    for cat_name, confidence in suggestions:
        cat = categories.get(cat_name.value)
        if cat:
            result.append(CategorySuggestion(
                category_name=cat_name.value,
                display_name=cat.display_name,
                confidence=round(confidence, 2),
            ))

    return CategorySuggestionResponse(suggestions=result)


@router.post("/recategorize", response_model=RecategorizeResponse)
async def recategorize_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-run categorizer on all uncategorized transactions for this user."""
    user_accounts = select(BankAccount.id).where(BankAccount.user_id == user.id)

    result = await db.execute(
        select(Transaction).where(
            Transaction.bank_account_id.in_(user_accounts),
            Transaction.category_id.is_(None),
        )
    )
    uncategorized = result.scalars().all()

    # Load category map
    cat_result = await db.execute(select(Category))
    categories = {c.name.value: c for c in cat_result.scalars().all()}

    updated = 0
    for txn in uncategorized:
        cat_name = infer_category(txn.description)
        if cat_name:
            category = categories.get(cat_name.value)
            if category:
                txn.category_id = category.id
                updated += 1

    await db.commit()

    return RecategorizeResponse(
        updated_count=updated,
        message=f"Re-categorized {updated} of {len(uncategorized)} uncategorized transactions",
    )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    bank_account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
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
    if category_name:
        # Filter by category name string
        cat_subq = select(Category.id).where(Category.name == category_name)
        conditions.append(Transaction.category_id.in_(cat_subq))
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
            selectinload(Transaction.statement),
        )
        .where(where_clause)
        .order_by(Transaction.transaction_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    txns = result.scalars().all()

    return TransactionListResponse(
        transactions=[_txn_to_response(t) for t in txns],
        total=total,
        page=page,
        page_size=page_size,
    )
