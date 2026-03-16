from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransactionCreate(BaseModel):
    bank_account_id: int
    transaction_type: str
    amount: float
    currency: str = "THB"
    description: Optional[str] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None
    reference: Optional[str] = None
    category_id: Optional[int] = None
    transaction_date: datetime


class TransactionUpdate(BaseModel):
    category_id: int


class TransactionResponse(BaseModel):
    id: int
    bank_account_id: int
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    transaction_type: str
    amount: float
    currency: str
    description: Optional[str] = None
    sender: Optional[str] = None
    receiver: Optional[str] = None
    reference: Optional[str] = None
    bank_name: Optional[str] = None
    statement_file_name: Optional[str] = None
    transaction_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


class CategoryResponse(BaseModel):
    id: int
    name: str
    display_name: str
    icon: Optional[str] = None

    model_config = {"from_attributes": True}


class CategorySuggestion(BaseModel):
    category_name: str
    display_name: str
    confidence: float


class CategorySuggestionRequest(BaseModel):
    description: str


class CategorySuggestionResponse(BaseModel):
    suggestions: list[CategorySuggestion]


class RecategorizeResponse(BaseModel):
    updated_count: int
    message: str
