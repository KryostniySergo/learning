from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Outbox settings
    producer_name: str = "auth-service"

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "auth-events"

    # Saga settings
    kafka_saga_commands_topic: str = "saga-commands"
    kafka_saga_replies_topic: str = "saga-replies"

    # JWT settings
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # DB settings
    db_name: str = "auth_db"
    db_port: int = 5432
    db_user: str = "postgres"
    db_pass: str
    db_host: str = "localhost"

    # SMTP settings
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@company-system.local"
    app_base_url: str = "http://localhost:8000"

    # Outbox retry settings
    outbox_max_retries: int = 5
    outbox_retry_base_seconds: int = 2
    kafka_dlq_topic: str = "dlq"

    @property
    def database_url(self) -> str:
        """database_url Возвращает connection string

        Returns:
            str: Connection string
        """
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
