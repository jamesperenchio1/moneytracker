import os
import uuid
import shutil
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
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

    # Trigger async processing
    from app.workers.tasks import process_statement

    process_statement.delay(stmt.id)

    return stmt


class FolderImportRequest(BaseModel):
    folder_path: str
    statement_type: str = "bank"


class FolderImportResponse(BaseModel):
    queued: int
    skipped: int
    files: list[str]


@router.post("/import-folder", response_model=FolderImportResponse)
async def import_folder(
    data: FolderImportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan a local folder and import any new PDF/CSV/XLSX files not yet processed."""
    folder = os.path.expanduser(data.folder_path)
    if not os.path.isdir(folder):
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder}")

    # Get already-imported filenames for this user to avoid duplication
    existing_result = await db.execute(
        select(Statement.file_name).where(Statement.user_id == user.id)
    )
    existing_names = {row[0] for row in existing_result.all()}

    upload_dir = os.path.join(settings.UPLOAD_DIR, str(user.id))
    os.makedirs(upload_dir, exist_ok=True)

    queued, skipped = 0, 0
    queued_files = []
    from app.workers.tasks import process_statement

    for fname in sorted(os.listdir(folder)):
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
        if ext not in ALLOWED_EXTENSIONS:
            continue
        if fname.startswith("."):
            continue

        if fname in existing_names:
            skipped += 1
            continue

        src = os.path.join(folder, fname)
        unique_name = f"{uuid.uuid4().hex}_{fname}"
        dest = os.path.join(upload_dir, unique_name)
        shutil.copy2(src, dest)

        stmt = Statement(
            user_id=user.id,
            statement_type=StatementType(data.statement_type),
            file_name=fname,
            file_path=dest,
            file_type=ext,
            status=StatementStatus.PENDING,
        )
        db.add(stmt)
        await db.flush()
        await db.refresh(stmt)
        process_statement.delay(stmt.id)

        queued += 1
        queued_files.append(fname)

    return FolderImportResponse(queued=queued, skipped=skipped, files=queued_files)


@router.get("", response_model=list[StatementResponse])
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


@router.delete("/{statement_id}", status_code=204)
async def delete_statement(
    statement_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a statement and its associated transactions."""
    from sqlalchemy import delete as sql_delete
    from app.models.transaction import Transaction

    result = await db.execute(
        select(Statement).where(Statement.id == statement_id, Statement.user_id == user.id)
    )
    stmt = result.scalar_one_or_none()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Delete associated bank transactions
    await db.execute(
        sql_delete(Transaction).where(Transaction.statement_id == statement_id)
    )

    # Delete the physical file if it exists
    if stmt.file_path and os.path.exists(stmt.file_path):
        try:
            os.remove(stmt.file_path)
        except OSError:
            pass

    await db.delete(stmt)
    await db.commit()
