from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    dashscope_api_key: str = ""
    qwen_model: str = "qwen-plus"

    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 604800  # 7 days
    cache_enabled: bool = True

    cors_origins: str = "*"

    # FC 默认监听 9000
    host: str = "0.0.0.0"
    port: int = 9000

    max_upload_size_mb: int = 10


settings = Settings()
