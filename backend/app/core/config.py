from pydantic_settings import BaseSettings
from typing import List, Optional, Any
import os
import logging

logger = logging.getLogger(__name__)

def get_secret(secret_name: str, default: Any = None) -> Any:
    """
    Get secret from Docker Secret file or environment variable.
    Prioritizes /run/secrets/{secret_name}.
    """
    secret_path = f"/run/secrets/{secret_name}"
    try:
        if os.path.exists(secret_path):
            with open(secret_path, "r") as f:
                return f.read().strip()
    except Exception as e:
        logger.warning(f"Could not read secret {secret_name}: {e}")
    
    return os.getenv(secret_name.upper(), default)

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and Docker Secrets.
    """
    
    # ============================================
    # Application Settings
    # ============================================
    APP_NAME: str = "OSINT Autonomous Analyst"
    VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000"
    ]
    
    # ============================================
    # Database Configuration
    # ============================================
    
    # Neo4j (Graph Database)
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = get_secret("neo4j_password", "osint_secure_password_change_me")
    NEO4J_DATABASE: str = "neo4j"
    
    # TimescaleDB (PostgreSQL)
    TIMESCALE_HOST: str = "localhost"
    TIMESCALE_PORT: int = 5432
    TIMESCALE_USER: str = "osint"
    TIMESCALE_PASSWORD: str = get_secret("timescale_password", "osint_timescale_password_change_me")
    TIMESCALE_DB: str = "osint_temporal"
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX_PREFIX: str = "oaa"
    
    # Weaviate (Vector Database)
    WEAVIATE_URL: str = "http://localhost:8080"
    
    # Redis (Cache & Rate Limiting)
    REDIS_PASSWORD: str = get_secret("redis_password", "osint_redis_password_change_me")
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://:{self.REDIS_PASSWORD}@localhost:6379/0"
    
    # MinIO (S3-compatible Object Storage)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "osint_admin"
    MINIO_SECRET_KEY: str = get_secret("minio_secret_key", "osint_minio_password_change_me")
    MINIO_SECURE: bool = False
    MINIO_BUCKET_RAW_DATA: str = "oaa-raw-data"
    MINIO_BUCKET_AUDIT: str = "oaa-audit-logs"
    
    # ============================================
    # LLM Configuration (Multi-Provider)
    # ============================================
    
    # Default reasoning provider
    DEFAULT_REASONING_PROVIDER: str = "claude"  # claude | gpt4 | llama
    
    # Claude
    ANTHROPIC_API_KEY: Optional[str] = get_secret("anthropic_api_key")
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20240620"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = get_secret("openai_api_key")
    GPT4_MODEL: str = "gpt-4-turbo-preview"
    
    # Llama (Local)
    LLAMA_ENDPOINT: Optional[str] = None
    LLAMA_MODEL: str = "llama-3-70b-instruct"
    
    # ============================================
    # Security & Compliance
    # ============================================
    
    # JWT Authentication
    SECRET_KEY: str = get_secret("app_secret_key", "CHANGE_ME_IN_PRODUCTION_TO_SECURE_RANDOM_STRING")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Compliance
    ENABLE_DENIED_ACTION_LOGGING: bool = True
    DEFAULT_RETENTION_DAYS: int = 2555  # 7 years for US
    
    # OpSec
    ENABLE_PROXY_ROTATION: bool = True
    ENABLE_TOR_ROUTING: bool = False  # Requires Tor setup
    TIMING_RANDOMIZATION_MIN_SEC: int = 5
    TIMING_RANDOMIZATION_MAX_SEC: int = 30
    
    # ============================================
    # Collection Agent Configuration
    # ============================================
    
    # Twitter/X
    TWITTER_BEARER_TOKEN: Optional[str] = get_secret("twitter_bearer_token")
    TWITTER_API_KEY: Optional[str] = get_secret("twitter_api_key")
    TWITTER_API_SECRET: Optional[str] = get_secret("twitter_api_secret")
    
    # Reddit
    REDDIT_CLIENT_ID: Optional[str] = get_secret("reddit_client_id")
    REDDIT_CLIENT_SECRET: Optional[str] = get_secret("reddit_client_secret")
    REDDIT_USER_AGENT: str = "OSINT Autonomous Analyst v0.1"
    
    # Shodan
    SHODAN_API_KEY: Optional[str] = get_secret("shodan_api_key")
    
    # Censys
    CENSYS_API_ID: Optional[str] = get_secret("censys_api_id")
    CENSYS_API_SECRET: Optional[str] = get_secret("censys_api_secret")
    
    # ============================================
    # Rate Limiting
    # ============================================
    
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10
    
    # Per-source rate limits (requests per minute)
    RATE_LIMIT_TWITTER: int = 15
    RATE_LIMIT_REDDIT: int = 60
    RATE_LIMIT_SHODAN: int = 1  # Shodan is very restrictive
    
    # ============================================
    # Proxy Configuration
    # ============================================
    
    PROXY_PROVIDER: Optional[str] = None  # brightdata | smartproxy | custom
    PROXY_USERNAME: Optional[str] = get_secret("proxy_username")
    PROXY_PASSWORD: Optional[str] = get_secret("proxy_password")
    PROXY_ENDPOINT: Optional[str] = None
    
    # ============================================
    # Logging
    # ============================================
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json | text
    LOG_TO_FILE: bool = True
    LOG_FILE_PATH: str = "/var/log/oaa/app.log"
    
    # ============================================
    # Feature Flags
    # ============================================
    
    ENABLE_HYPOTHESIS_GENERATION: bool = True
    ENABLE_DARK_WEB_COLLECTION: bool = False  # Requires Tor setup
    ENABLE_GEOSPATIAL_ANALYTICS: bool = True
    ENABLE_NARRATIVE_ANALYSIS: bool = True
    
    # ============================================
    # Performance
    # ============================================
    
    MAX_GRAPH_TRAVERSAL_DEPTH: int = 3
    MAX_ENTITIES_PER_QUERY: int = 1000
    QUERY_TIMEOUT_SECONDS: int = 30
    
    # ============================================
    # Computed Properties
    # ============================================
    
    @property
    def timescale_dsn(self) -> str:
        """PostgreSQL connection string"""
        return f"postgresql://{self.TIMESCALE_USER}:{self.TIMESCALE_PASSWORD}@{self.TIMESCALE_HOST}:{self.TIMESCALE_PORT}/{self.TIMESCALE_DB}"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# ============================================
# Global Settings Instance
# ============================================

settings = Settings()
