import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX: Optional[str] = "tender-analysis"
    
    # Server Config
    PORT: int = 3000
    NODE_ENV: str = "development"
    MAX_FILE_SIZE_MB: int = 50
    
    # Database Config (PostgreSQL) - Kept for migration period
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "12345"  # Match your PostgreSQL password
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "Bid2"  # Main database for Bid Intelligence project
    DATABASE_URL: Optional[str] = None
    
    # MongoDB Config
    MONGODB_STRING: Optional[str] = None  # Connection string from .env
    MONGODB_DB: str = "bid_intelligence"  # Database name in MongoDB
    
    # Versioning
    PROCESSING_VERSION: int = 31
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.DATA_DIR, exist_ok=True)
