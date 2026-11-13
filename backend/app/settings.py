from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: list[str] = []
    database_path: Path = Path("data/orbitops.sqlite3")\n    spice_kernel_storage_path: Path = Path("data/spice-kernels")


settings = Settings()
