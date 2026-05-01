"""
Central settings loaded from environment variables / .env file.
"""
import os
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM — local Ollama by default, no API key required
    agent_model: str = "ollama/gemma4:26b"
    ollama_api_base: str = "http://localhost:11434"

    # Optional cloud provider keys (only needed if switching AGENT_MODEL)
    openrouter_api_key: str = ""
    moonshot_api_key: str = ""
    google_api_key: str = ""

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

    @model_validator(mode="after")
    def _export_ollama_env(self) -> "Settings":
        # LiteLLM (used by CrewAI) reads OLLAMA_API_BASE to locate the local server.
        os.environ.setdefault("OLLAMA_API_BASE", self.ollama_api_base)
        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
