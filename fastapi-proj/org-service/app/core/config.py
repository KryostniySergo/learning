from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Outbox settings
    producer_name: str = "org-service"

    # Inbox settings
    consumer_name: str = "org-service"

    # Kafka settings
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_topic: str = "auth-events"
    kafka_consumer_group: str = "org-service"

    # DB settings
    db_name: str
    db_port: int = 5432
    db_user: str
    db_pass: str
    db_host: str = "localhost"

    @property
    def database_url(self) -> str:
        """database_url Возвращает connection string

        Returns:
            str: Connection string
        """
        return f"postgresql+asyncpg://{self.db_user}:{self.db_pass}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
