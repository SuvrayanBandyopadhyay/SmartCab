from fastapi import FastAPI

from app.auth.router import router as auth_router
from app.auth.test_router import router as test_auth_router
from app.cablang.router import router as cablang_router
from app.ai.router import router as chat_router

app = FastAPI(
    title="SmartCab",
    description="AI-Powered Employee Transport Management",
    version="0.3.0",
)

app.include_router(auth_router)
app.include_router(test_auth_router)
app.include_router(cablang_router)
app.include_router(chat_router)

@app.get("/health")
def health():
    return {
        "application": "SmartCab",
        "status": "healthy",
    }