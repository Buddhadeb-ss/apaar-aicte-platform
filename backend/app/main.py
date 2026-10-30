import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .database.session import engine, Base, SessionLocal, ensure_schema_migrations
from .database.seed_data import seed_database

# Version 1 Routers
from .api.v1 import (
    health as v1_health,
    auth as v1_auth,
    institutions as v1_institutions,
    intakes as v1_intakes,
    students as v1_students,
    upload_jobs as v1_upload_jobs,
    validation as v1_validation,
    dashboard as v1_dashboard,
    verifications as v1_verifications,
    reports as v1_reports
)

# Compatibility Routers for existing frontend
from .api import (
    auth as compat_auth,
    aicte_admin as compat_aicte,
    institutions as compat_institutions,
    students as compat_students,
    import_export as compat_import,
    verification as compat_verification,
    reports as compat_reports
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure persistent SQLite schema exists
    Base.metadata.create_all(bind=engine)
    ensure_schema_migrations(engine)
    # Seed synthetic realistic records if empty
    db = SessionLocal()
    try:
        seed_database(db, force_reset=False)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="SIH26263: Real Persistent Backend for APAAR ID-Based Student Data Management & Verification Platform for AICTE-Approved Institutions.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Version 1 API (/api/v1) -----------------
app.include_router(v1_health.router, prefix="/api/v1")
app.include_router(v1_auth.router, prefix="/api/v1")
app.include_router(v1_institutions.router, prefix="/api/v1")
app.include_router(v1_intakes.router, prefix="/api/v1")
app.include_router(v1_students.router, prefix="/api/v1")
app.include_router(v1_upload_jobs.router, prefix="/api/v1")
app.include_router(v1_validation.router, prefix="/api/v1")
app.include_router(v1_dashboard.router, prefix="/api/v1")
app.include_router(v1_verifications.router, prefix="/api/v1")
app.include_router(v1_reports.router, prefix="/api/v1")

# ----------------- Frontend Compatibility Routers (/api) -----------------
app.include_router(compat_auth.router, prefix="/api")
app.include_router(compat_aicte.router, prefix="/api")
app.include_router(compat_institutions.router, prefix="/api")
app.include_router(compat_students.router, prefix="/api")
app.include_router(compat_import.router, prefix="/api")
app.include_router(compat_verification.router, prefix="/api")
app.include_router(compat_reports.router, prefix="/api")

@app.get("/api/health", tags=["Health & Readiness Probes"])
def compat_health_check():
    """Health endpoint alias for frontend and monitoring probes."""
    db_connected = False
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "HEALTHY" if db_connected else "DEGRADED",
        "service": settings.PROJECT_NAME,
        "problem_statement": settings.PROBLEM_STATEMENT,
        "version": settings.VERSION,
        "database_connected": db_connected,
        "simulated_gateway": settings.APAAR_GATEWAY_SIMULATED,
        "gateway_provider": settings.GATEWAY_PROVIDER
    }

# ----------------- Static SPA Mount -----------------
dist_dir = os.path.join(os.path.dirname(settings.BASE_DIR), "frontend", "dist")
if os.path.isdir(dist_dir):
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = os.path.join(dist_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(dist_dir, "index.html"))
