import time
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1 import negotiate, merchant, webhooks
from app.engine.guardrails import FinancialGuardrailException
from app.audit.logger import log_audit_event

# Configure logging format for explainable audit tracking
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("a2a_main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown lifecycle events.
    Verifies critical configuration (Razorpay API keys) before booting.
    """
    logger.info("Starting up Razorpay Agent-to-Agent Negotiator Engine...")
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.warning("Razorpay API keys not set! Operating in mock mode.")
    else:
        logger.info("Razorpay API client initialized successfully.")
    
    yield
    
    logger.info("Shutting down Agent-to-Agent Negotiator Engine...")


# Initialize FastAPI instance
app = FastAPI(
    title="Razorpay A2A Dynamic Negotiator Engine",
    description="B2B Agentic Commerce API. Enables bounded, explainable agent-to-agent negotiations with native Razorpay payment links.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup for web dashboard access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Middleware: Performance & Audit Context Injection
@app.middleware("http")
async def add_audit_context_and_timing(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-MS"] = f"{process_time:.2f}"
    
    return response


# ROUTER REGISTER
app.include_router(negotiate.router, prefix="/api/v1/negotiate", tags=["A2A Negotiation"])
app.include_router(merchant.router, prefix="/api/v1/merchant", tags=["Merchant Guardrails & Rules"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Razorpay Webhooks"])


# EXCEPTION HANDLER 1: Financial Guardrail Breaches (Bounded & Gated Rule)
@app.exception_handler(FinancialGuardrailException)
async def guardrail_exception_handler(request: Request, exc: FinancialGuardrailException):
    req_id = getattr(request.state, "request_id", "unknown")
    
    # Audit log the exact failure reason
    log_audit_event(
        negotiation_id=exc.negotiation_id or req_id,
        action="GUARDRAIL_INTERVENTION",
        requested_amount=exc.requested_price,
        status="REJECTED_BOUND_BREACH",
        reasoning=str(exc)
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "REJECTED",
            "code": "FINANCIAL_BOUND_BREACH",
            "message": str(exc),
            "floor_counter_offer": exc.floor_price,
            "explainability": {
                "gated_by": "MarginGuardrailV1",
                "reason": f"Offered ₹{exc.requested_price} is below absolute floor price of ₹{exc.floor_price}."
            }
        }
    )


# EXCEPTION HANDLER 2: Graceful Gateway Failure Recovery
@app.exception_handler(Exception)
async def global_graceful_failure_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{req_id}] Unhandled System Exception: {str(exc)}", exc_info=True)
    
    # Return structured failure payload without crashing agentic workflow
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status": "SERVICE_DEGRADED",
            "code": "AGENT_SYSTEM_ERROR",
            "message": "The negotiation engine encountered a transient error.",
            "recovery_action": "Retry negotiation payload with request_id attached.",
            "request_id": req_id
        }
    )


# System Health Check Endpoint
@app.get("/health", tags=["System Check"])
async def health_check():
    return {
        "status": "active",
        "service": "Razorpay A2A Negotiator Engine",
        "track": "Track 1 - AI Growth & Agentic Commerce",
        "features": ["Bounded Financial Actions","Structured Audit Trail", "Failure Handling"]
    }