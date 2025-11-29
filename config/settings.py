"""
Configuration Management Module
Centralized configuration using Pydantic Settings
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application Settings
    app_name: str = "FMCG Enterprise Agent"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # API Settings
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    api_workers: int = 4
    
    # Google Gemini
    google_api_key: str = Field(..., description="Google API Key")
    google_project_id: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 8192
    
    # Database
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50
    redis_session_ttl: int = 3600
    
    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = "agent_exchange"
    rabbitmq_queue_prefix: str = "agent_"
    
    # Vector Database
    chroma_persist_directory: str = "./data/chroma"
    chroma_collection_name: str = "fmcg_memory"
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # Session Management
    session_timeout: int = 1800
    session_cleanup_interval: int = 300
    max_sessions_per_user: int = 5
    
    # Memory Configuration
    memory_bank_size: int = 1000
    memory_retention_days: int = 90
    context_window_size: int = 4096
    enable_context_compaction: bool = True
    
    # Agent Configuration
    max_parallel_agents: int = 5
    agent_timeout: int = 300
    enable_long_running_ops: bool = True
    checkpoint_interval: int = 60
    
    # Observability
    enable_tracing: bool = True
    enable_metrics: bool = True
    otlp_endpoint: str = "http://localhost:4317"
    prometheus_port: int = 9090
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    
    # Logging
    log_format: str = "json"
    log_file: str = "./logs/agent.log"
    log_rotation: str = "10 MB"
    log_retention: int = 30
    
    # Security
    secret_key: str = Field(..., description="Secret key for JWT")
    jwt_algorithm: str = "HS256"
    jwt_expiration: int = 3600
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    
    # Tools
    enable_google_search: bool = True
    enable_code_execution: bool = True
    enable_mcp: bool = True
    google_search_api_key: Optional[str] = None
    google_search_engine_id: Optional[str] = None
    
    # Evaluation
    enable_evaluation: bool = True
    evaluation_sample_rate: float = 0.1
    evaluation_metrics_interval: int = 3600
    
    # A2A Protocol
    a2a_enabled: bool = True
    a2a_port: int = 8001
    a2a_discovery_enabled: bool = True
    a2a_heartbeat_interval: int = 30
    
    # Data Settings
    sample_data_path: str = "./data/sample_fmcg_data.csv"
    data_refresh_interval: int = 3600
    enable_data_caching: bool = True
    
    # Feature Flags
    feature_parallel_agents: bool = True
    feature_sequential_agents: bool = True
    feature_loop_agents: bool = True
    feature_pause_resume: bool = True
    feature_memory_bank: bool = True
    feature_context_compaction: bool = True
    
    # Performance
    max_concurrent_requests: int = 100
    request_timeout: int = 30
    worker_threads: int = 4
    enable_async_io: bool = True
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
