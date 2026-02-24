from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    database_url: str


    EMAIL_HOST: str | None = None
    EMAIL_PORT: int = 587
    EMAIL_USER: str | None = None
    EMAIL_PASS: str | None = None
    EMAIL_FROM: str | None = None
    EMAIL_TO: str | None = None  

    # Security
    SECRET_KEY: str = "something"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"

settings = Settings()

    

 