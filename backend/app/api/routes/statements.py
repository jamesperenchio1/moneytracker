import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.statement import Statement, StatementType, StatementStatus
from app.schemas.statement import StatementResponse

settings = get_settings()
router = APIRouter(prefix="/statements", tags=["statements"])

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "pdf"}


@router.post("/upload", response_model=StatementResponse, status_code=201)
async def upload_statement(
    file: UploadFile = File(...),
    statement_type: str = Form(...),
    institution_code: str = Form(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate file extension
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type .{ext} not supported. Use: {ALLOWED_EXTENSIONS}")

    # Validate file size
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB}MB")

    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
    os.makedirs(upload_dir, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create statement record
    stmt = Statement(
        user_id=user.id,
        statement_type=StatementType(statement_type),
        institution_code=institution_code,
        file_name=file.filename,
        file_path=file_path,
        file_type=ext,
        status=StatementStatus.PENDING,
    )
    db.add(stmt)
    await db.flush()
    await db.refresh(stmt)
    await db.commit()

    # Trigger async processing — tolerate broker being unavailable in dev
    try:
        from app.workers.tasks import process_statement
        process_statement.delay(stmt.id)
    except Exception:
        pass  # Celery will pick it up on next retry, or statement stays PENDING

    return stmt


@router.get("/", response_model=list[StatementResponse])
async def list_statements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Statement).where(Statement.user_id == user.id).order_by(Statement.uploaded_at.desc())
    )
    return result.scalars().all()


@router.get("/{statement_id}", response_model=StatementResponse)
async def get_statement(
    statement_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Statement).where(Statement.id == statement_id, Statement.user_id == user.id)
    )
    stmt = result.scalar_one_or_none()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    return stmt
