from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://deadresult:deadresult@localhost:5432/deadresult"
    database_url_sync: str = "postgresql://deadresult:deadresult@localhost:5432/deadresult"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    embedding_dim: int = 384  # all-MiniLM-L6-v2 dimension
    default_page_size: int = 20
    max_page_size: int = 100
    s3_bucket: str = ""
    aws_region: str = "us-east-1"

    model_config = {"env_prefix": "DEADRESULT_"}


settings = Settings()
