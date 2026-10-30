from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...database.session import get_db
from ...database.models import Institution, Student, StudentEnrolment
from ...core.config import settings

router = APIRouter(prefix="/health", tags=["Health & Readiness Probes"])

@router.get("")
def health_check(db: Session = Depends(get_db)):
    """System liveness and readiness probe verifying database connectivity and records."""
    db_ok = False
    inst_count = 0
    enrolment_count = 0
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        inst_count = db.query(Institution).count()
        enrolment_count = db.query(StudentEnrolment).count()
    except Exception:
        db_ok = False

    return {
        "status": "HEALTHY" if db_ok else "DEGRADED",
        "service": settings.PROJECT_NAME,
        "problem_statement": settings.PROBLEM_STATEMENT,
        "version": settings.VERSION,
        "database_connected": db_ok,
        "persistent_records": {
            "institutions_loaded": inst_count,
            "enrolments_loaded": enrolment_count
        },
        "simulated_gateway": settings.APAAR_GATEWAY_SIMULATED,
        "gateway_provider": settings.GATEWAY_PROVIDER
    }
