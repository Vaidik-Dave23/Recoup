from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Recovery agent (Gemini + LangGraph)
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    recovery_confidence_threshold: float = 0.55
    recovery_max_attempts: int = 3

    # Execution channel (optional SMTP delivery)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
