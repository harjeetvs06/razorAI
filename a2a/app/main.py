"""RazorAI – A2A Negotiator  |  FastAPI entrypoint"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import negotiate, merchant, webhooks
from app.config import settings

app = FastAPI(
    title="RazorAI A2A Negotiator",
    description="Agent-to-Agent autonomous price negotiation engine with Razorpay payment links.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(negotiate.router, prefix="/api/v1/negotiate", tags=["Negotiation"])
app.include_router(merchant.router,  prefix="/api/v1/merchant",  tags=["Merchant"])
app.include_router(webhooks.router,  prefix="/api/v1/webhooks",  tags=["Webhooks"])


@app.get("/", tags=["Health"])
async def health():
    return {"service": "RazorAI A2A Negotiator", "version": "1.0.0", "status": "live"}
