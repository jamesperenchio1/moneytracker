import json
from pydantic import BaseModel, field_validator
from typing import Optional, Any
from datetime import datetime


class AuditEntry(BaseModel):
    step: str
    ts: str
    level: str  # info | warn | error
    detail: str
    # Optional row-level fields
    index: Optional[int] = None
    date: Optional[str] = None
    amount: Optional[float] = None
    txn_type: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    action: Optional[str] = None    # brokerage rows
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    skipped: Optional[bool] = None
    skip_reason: Optional[str] = None
    # Parser info
    expected: Optional[str] = None
    parser_name: Optional[str] = None


class StatementResponse(BaseModel):
    id: int
    statement_type: str
    institution_code: Optional[str] = None
    file_name: str
    file_type: str
    status: str
    error_message: Optional[str] = None
    audit_log: Optional[list[AuditEntry]] = None
    records_processed: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_validator("audit_log", mode="before")
    @classmethod
    def parse_audit_log(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return v
