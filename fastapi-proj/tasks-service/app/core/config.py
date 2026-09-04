from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Outbox settings
    producer_name: str = "tasks-service"

    # Inbox settings
    consumer_name: str = "tasks-service"

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic: str = "tasks-events"
    kafka_consumer_topic: str = "auth-events"
    kafka_consumer_group: str = "tasks-service"

    # JWT settings
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

    # DB settings
    db_name: str
    db_port: int = 5434
    db_user: str
    db_pass: str
    db_host: str = "localhost"

    @property
    def database_url(self) -> str:
        """Возвращает connection string для asyncpg.

        Returns:
            str: строка подключения к БД.
        """
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()  # type: ignore[call-arg]
