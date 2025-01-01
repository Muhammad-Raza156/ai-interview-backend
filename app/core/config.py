from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str = "aws-0-ap-south-1.pooler.supabase.com"
    DB_PORT: int = 5432
    SECRET_KEY: str = ""
    COHERE_API_KEY: str = ""
    API_VERSION: str
    database_url: str
    DB_URL: str
    

    class Config:
        env_file = ".env"


settings = Settings()
