"""
Orizon Zero Trust Connect - Configuration
For: Marco @ Syneto/Orizon
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    APP_NAME: str = "Orizon Zero Trust Connect"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    
    # API
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: str = Field(default="http://localhost:8000", env="API_BASE_URL")
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")  # For provision tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://46.101.128.1",
        "https://46.101.189.126"
    ]
    
    # Database - PostgreSQL
    POSTGRES_SERVER: str = Field(default="localhost", env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(default="orizon", env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default="orizon_ztc", env="POSTGRES_DB")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # Database - MongoDB (for logs and audit trail)
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        env="MONGODB_URL"
    )
    MONGODB_DB: str = Field(default="orizon_logs", env="MONGODB_DB")
    
    # Redis
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # Tunnel Configuration
    TUNNEL_SSH_PORT: int = Field(default=2222, env="TUNNEL_SSH_PORT")
    TUNNEL_HTTPS_PORT: int = Field(default=8443, env="TUNNEL_HTTPS_PORT")
    TUNNEL_HUB_HOST: str = Field(default="46.101.189.126", env="TUNNEL_HUB_HOST")

    # Aliases for provisioning
    @property
    def HUB_HOST(self) -> str:
        return self.TUNNEL_HUB_HOST

    @property
    def HUB_SSH_PORT(self) -> int:
        return self.TUNNEL_SSH_PORT
    
    # SSH Server Configuration
    SSH_HOST_KEY_PATH: str = Field(
        default="/etc/orizon/ssh_host_key",
        env="SSH_HOST_KEY_PATH"
    )
    SSH_AUTHORIZED_KEYS_PATH: str = Field(
        default="/etc/orizon/authorized_keys",
        env="SSH_AUTHORIZED_KEYS_PATH"
    )
    
    # Security
    ALGORITHM: str = "HS256"
    BCRYPT_ROUNDS: int = 12
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="/var/log/orizon/app.log", env="LOG_FILE")
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30  # seconds
    WS_MAX_CONNECTIONS: int = 10000
    
    # Celery
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        env="CELERY_RESULT_BACKEND"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
