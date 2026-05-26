from pydantic import PostgresDsn, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    SQL_USER: str
    SQL_PASSWORD: str
    SQL_HOST: str
    SQL_PORT: int = 5432
    SQL_DB: str

    # Connection Pool (Infra Shield)
    DB_POOL_MIN_SIZE: int = 20
    DB_POOL_MAX_SIZE: int = 100
    DB_POOL_TIMEOUT: int = 10  # seconds to wait for pool slot

    # Rate Limit
    RATE_LIMIT_PER_MINUTE: int = 5

    # Layer 4 Base URL (defined in travel.env, added here)
    LAYER4_BASE_URL: str = "http://host.docker.internal:8000"
    SOLVER_TIMEOUT: float = 120.0

    # LLM Configuration
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Firebase Admin SDK Configuration
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_PATH: str = ""  # Path to service account JSON (gitignored)

    @computed_field
    @property
    def sql_url(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.SQL_USER,
            password=self.SQL_PASSWORD,
            host=self.SQL_HOST,
            port=self.SQL_PORT,
            path=self.SQL_DB,
        )

    def get_conn_str(self):
        return f"dbname={self.SQL_DB} user={self.SQL_USER} password={self.SQL_PASSWORD} host={self.SQL_HOST} port={self.SQL_PORT}"


settings = Settings()
