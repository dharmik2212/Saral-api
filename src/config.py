from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "saral"

    # Apify
    apify_api_key: str = ""
    apify_actor_id: str = "GOvL4O4RwFqsdIqXF"

    # Pipeline
    max_concurrent: int = 10
    batch_size: int = 50
    batch_urls_per_run: int = 50
    max_retries: int = 3

    # Paths
    data_dir: str = "data"
    cache_dir: str = "data/cache"
    logs_dir: str = "data/logs"
    raw_csv: str = "missing_duration_candidates.csv"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
