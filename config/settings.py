"""
Central settings loaded from environment variables / .env file.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM — Google Gemini
    google_api_key: str = ""
    gemini_model: str = "gemini/gemini-1.5-pro"

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""

    # Kubernetes
    kubeconfig: str = ""
    k8s_namespace: str = "default"

    # Prometheus / Alertmanager
    prometheus_url: str = "http://localhost:9090"
    alertmanager_url: str = "http://localhost:9093"

    # AWS
    aws_default_region: str = "us-east-1"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    approval_gate_enabled: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
