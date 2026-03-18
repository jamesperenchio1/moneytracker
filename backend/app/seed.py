"""Seed the database with initial reference data."""

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import Base
from app.models.bank import Bank, BankName
from app.models.brokerage import Brokerage, BrokerageName
from app.models.transaction import Category, CategoryName

settings = get_settings()
engine = create_engine(settings.database_url_sync)


def seed():
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        # Seed banks
        banks = [
            {"name": "Bangkok Bank", "code": BankName.BANGKOK_BANK, "country": "TH"},
            {"name": "Kasikorn Bank", "code": BankName.KASIKORN, "country": "TH"},
            {"name": "Siam Commercial Bank", "code": BankName.SCB, "country": "TH"},
            {"name": "Krungsri", "code": BankName.KRUNGSRI, "country": "TH"},
            {"name": "Krungthai Bank", "code": BankName.KRUNGTHAI, "country": "TH"},
            {"name": "TTB", "code": BankName.TTB, "country": "TH"},
        ]
        for b in banks:
            exists = db.execute(select(Bank).where(Bank.code == b["code"])).scalar_one_or_none()
            if not exists:
                db.add(Bank(**b))

        # Seed brokerages
        brokerages = [
            {"name": "Webull USA", "code": BrokerageName.WEBULL_USA, "country": "US", "api_supported": False, "scraping_supported": True},
            {"name": "Webull Thailand", "code": BrokerageName.WEBULL_TH, "country": "TH", "api_supported": False, "scraping_supported": True},
            {"name": "Dime", "code": BrokerageName.DIME, "country": "TH", "api_supported": False, "scraping_supported": False},
        ]
        for b in brokerages:
            exists = db.execute(select(Brokerage).where(Brokerage.code == b["code"])).scalar_one_or_none()
            if not exists:
                db.add(Brokerage(**b))

        # Seed categories
        categories = [
            {"name": CategoryName.FOOD, "display_name": "Food & Dining", "icon": "utensils"},
            {"name": CategoryName.RENT, "display_name": "Rent & Housing", "icon": "home"},
            {"name": CategoryName.TRANSPORTATION, "display_name": "Transportation", "icon": "car"},
            {"name": CategoryName.UTILITIES, "display_name": "Utilities", "icon": "bolt"},
            {"name": CategoryName.SUBSCRIPTIONS, "display_name": "Subscriptions", "icon": "refresh"},
            {"name": CategoryName.INCOME, "display_name": "Income", "icon": "wallet"},
            {"name": CategoryName.TRANSFERS, "display_name": "Transfers", "icon": "arrows-rotate"},
            {"name": CategoryName.TRANSFER_IN, "display_name": "Transfer In", "icon": "arrow-down-left"},
            {"name": CategoryName.TRANSFER_OUT, "display_name": "Transfer Out", "icon": "arrow-up-right"},
            {"name": CategoryName.SHOPPING, "display_name": "Shopping", "icon": "bag-shopping"},
            {"name": CategoryName.ENTERTAINMENT, "display_name": "Entertainment", "icon": "film"},
            {"name": CategoryName.HEALTHCARE, "display_name": "Healthcare", "icon": "heart-pulse"},
            {"name": CategoryName.EDUCATION, "display_name": "Education", "icon": "graduation-cap"},
            {"name": CategoryName.INVESTMENT, "display_name": "Investments", "icon": "chart-line"},
            {"name": CategoryName.CREDIT_CARD_PAYMENT, "display_name": "Credit Card Payment", "icon": "credit-card"},
            {"name": CategoryName.OTHER, "display_name": "Other", "icon": "ellipsis"},
        ]
        for c in categories:
            exists = db.execute(select(Category).where(Category.name == c["name"])).scalar_one_or_none()
            if not exists:
                db.add(Category(**c))

        db.commit()
        print("Database seeded successfully!")


if __name__ == "__main__":
    seed()
