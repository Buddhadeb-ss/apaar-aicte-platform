import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "AICTE APAAR Student Data Management & Verification Platform"
    PROBLEM_STATEMENT: str = "SIH26263"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "aicte_sih26263_super_secret_cryptographic_key_98472")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours
    
    # SQLite Database Persistence
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DEFAULT_DB_PATH = os.path.join(BASE_DIR, "apaar_platform.db").replace("\\", "/")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]
    
    # Simulated APAAR / ABC / DigiLocker Gateway
    APAAR_GATEWAY_SIMULATED: bool = True
    GATEWAY_PROVIDER: str = "DigiLocker / ABC National Academic Depository (Simulated Gateway v2.4)"

settings = Settings()
