from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения: настройки Kafka, DB, SMTP и других сервисов."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    # Outbox settings
    producer_name: str = "org-service"

    # Inbox settings
    consumer_name: str = "org-service"

    # Saga settings
    kafka_saga_commands_topic: str = "saga-commands"
    kafka_saga_replies_topic: str = "saga-replies"

    # JWT settings
    jwt_secret: str
    jwt_algorithm: str = "HS256"

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "org-events"
    kafka_consumer_topic: str = "auth-events"
    kafka_consumer_group: str = "org-service"

    # DB settings
    db_name: str = "org_db"
    db_port: int = 5433
    db_user: str = "postgres"
    db_pass: str
    db_host: str = "localhost"

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
