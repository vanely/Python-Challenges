from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTES_", env_file=".env")

    app_name: str = "Notes API"
    max_page: int = 100


settings = Settings()
