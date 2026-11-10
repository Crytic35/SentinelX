from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.api.config import settings
from services.api.routers import agents, security, payments, attack_lab, policies, merchants, tools, analyst
from database.session import engine, Base
from database.seed import seed_database
from database.session import SessionLocal

# Ensure tables and seed data exist
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SentinelX: Zero-Trust Security Layer for AI Payment Agents (PayPal AI Hackathon)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(agents.router, prefix=settings.API_PREFIX)
app.include_router(security.router, prefix=settings.API_PREFIX)
app.include_router(payments.router, prefix=settings.API_PREFIX)
app.include_router(attack_lab.router, prefix=settings.API_PREFIX)
app.include_router(policies.router, prefix=settings.API_PREFIX)
app.include_router(merchants.router, prefix=settings.API_PREFIX)
app.include_router(tools.router, prefix=settings.API_PREFIX)
app.include_router(analyst.router, prefix=settings.API_PREFIX)

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SentinelX Gateway API",
        "version": settings.VERSION,
        "paypal_mode": settings.PAYPAL_MODE,
        "shadow_mode": settings.SHADOW_MODE,
        "global_freeze": settings.GLOBAL_FREEZE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.api.main:app", host="0.0.0.0", port=8000, reload=True)

