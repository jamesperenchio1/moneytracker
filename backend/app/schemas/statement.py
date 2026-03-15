from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StatementResponse(BaseModel):
    id: int
    statement_type: str
    institution_code: Optional[str] = None
    file_name: str
    file_type: str
    status: str
    error_message: Optional[str] = None
    records_processed: int
    uploaded_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
