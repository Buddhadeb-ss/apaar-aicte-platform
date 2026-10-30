from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings

# SQLite connection args for multi-threaded FastAPI access
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

# Enable Foreign Keys and WAL Mode in SQLite for concurrency & integrity
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_schema_migrations(engine):
    """Safely applies SQLite column additions for incremental model changes without data loss."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(validation_issues)")).fetchall()
            existing_cols = {row[1] for row in result}
            if existing_cols:
                migrations = [
                    ("institution_id", "TEXT"),
                    ("student_id", "TEXT"),
                    ("enrolment_id", "TEXT"),
                    ("rule_id", "TEXT DEFAULT 'RULE_UNKNOWN'"),
                    ("suggested_remediation", "TEXT"),
                    ("anomaly_score", "REAL DEFAULT 0.0"),
                    ("reviewed_by_user_id", "TEXT"),
                    ("reviewed_by_email", "TEXT"),
                    ("reviewed_at", "DATETIME"),
                    ("resolution_reason", "TEXT"),
                    ("created_at", "DATETIME"),
                    ("updated_at", "DATETIME"),
                ]
                for col_name, col_type in migrations:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE validation_issues ADD COLUMN {col_name} {col_type}"))
                conn.commit()
        except Exception as e:
            pass

def get_db():
    """Dependency that yields a database session and safely closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
