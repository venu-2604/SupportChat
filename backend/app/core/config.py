from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    ENV: str = "development"
    API_PREFIX: str = "/api"

    JWT_SECRET: str = "change_me_dev_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "csupport"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"

    MONGO_URI: str = "mongodb://mongo:27017"
    MONGO_DB: str = "csupport"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    TWOFA_ISSUER: str = "CSupport"

    OPENAI_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None


settings = Settings()


