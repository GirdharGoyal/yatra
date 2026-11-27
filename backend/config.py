from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Yatra AI Travel App"
    database_url: str = "sqlite:///./yatra.db"
    jwt_secret: str = "yatra-dev-secret-key-2026"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    model_name: str = "gemini-2.5-flash"
    api_base_url: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
