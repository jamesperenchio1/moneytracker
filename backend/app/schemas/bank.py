from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BankAccountCreate(BaseModel):
    bank_id: int
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    currency: str = "THB"


class BankAccountResponse(BaseModel):
    id: int
    bank_id: int
    bank_name: Optional[str] = None
    bank_code: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    balance: float
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BankResponse(BaseModel):
    id: int
    name: str
    code: str
    country: str

    model_config = {"from_attributes": True}
