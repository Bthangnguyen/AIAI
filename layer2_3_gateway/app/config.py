from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True, extra="ignore"
    )

    SQL_USER: str
    SQL_PASSWORD: str
    SQL_HOST: str
    SQL_DB: str

    # Connection Pool (Infra Shield)
    DB_POOL_MIN_SIZE: int = 20
    DB_POOL_MAX_SIZE: int = 100
    DB_POOL_TIMEOUT: int = 10  # seconds to wait for pool slot

    # Rate Limit
    RATE_LIMIT_PER_MINUTE: int = 5

    # Layer 4 Base URL (defined in travel.env, added here)
    LAYER4_BASE_URL: str = "http://host.docker.internal:8000"

    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    @computed_field
    @property
    def sql_url(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.SQL_USER,
            password=self.SQL_PASSWORD,
            host=self.SQL_HOST,
            path=self.SQL_DB,
        )

    def get_conn_str(self):
        return f"dbname={self.SQL_DB} user={self.SQL_USER} password={self.SQL_PASSWORD} host={self.SQL_HOST} port=5432"


settings = Settings()
