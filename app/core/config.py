from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str = "aws-0-ap-south-1.pooler.supabase.com"
    DB_PORT: int = 5432
    SECRET_KEY: str = ""
    ALGORITHM: str
    COHERE_API_KEY: str = ""
    API_VERSION: str
    DATABASE_URL: str
    DB_URL: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_URL: str
    CACHE_EXPIRATION: int
    

    class Config:
        env_file = ".env"


settings = Settings()
