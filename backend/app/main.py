from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import auth, banks, transactions, portfolio, statements, analytics

settings = get_settings()

app = FastAPI(
    title="MoneyTracker API",
    description="Smart Money Tracker for investments and banking in Thailand",
    version="1.0.0",
    redirect_slashes=False,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(banks.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(portfolio.router, prefix="/api")
app.include_router(statements.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
