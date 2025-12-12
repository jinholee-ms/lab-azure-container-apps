import argparse
import asyncio
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.console import Console


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    AZURE_AI_FOUNDRY_PROJECT_ENDPOINT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_AI_FOUNDRY_PROJECT_ENDPOINT")
    )
    AZURE_OPENAI_ENDPOINT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_ENDPOINT")
    )
    AZURE_OPENAI_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_API_KEY")
    )
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_CHAT_DEPLOYMENT")
    )
    AZURE_OPENAI_CHAT_MINI_DEPLOYMENT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_CHAT_MINI_DEPLOYMENT")
    )
    AZURE_OPENAI_REASONING_DEPLOYMENT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_REASONING_DEPLOYMENT")
    )
    AZURE_OPENAI_REASONING_MINI_DEPLOYMENT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_REASONING_MINI_DEPLOYMENT")
    )
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_API_VERSION")
    )
    AZURE_DOCUMENTINTELLIGENCE_ENDPOINT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_DOCUMENTINTELLIGENCE_ENDPOINT")
    )
    AZURE_DOCUMENTINTELLIGENCE_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("AZURE_DOCUMENTINTELLIGENCE_API_KEY")
    )
    AZURE_OPENAI_MULTIMEDIA_ENDPOINT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_MULTIMEDIA_ENDPOINT")
    )
    AZURE_OPENAI_MULTIMEDIA_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("AZURE_OPENAI_MULTIMEDIA_API_KEY")
    )
    AZURE_AI_SEARCH_ENDPOINT: str = Field(
        ..., validation_alias=AliasChoices("AZURE_AI_SEARCH_ENDPOINT")
    )
    AZURE_AI_SEARCH_ADMIN_KEY: str = Field(
        ..., validation_alias=AliasChoices("AZURE_AI_SEARCH_ADMIN_KEY")
    )
    NAVER_DEV_CLIENT_ID: str = Field(
        ..., validation_alias=AliasChoices("NAVER_DEV_CLIENT_ID")
    )
    NAVER_DEV_CLIENT_SECRET: str = Field(
        ..., validation_alias=AliasChoices("NAVER_DEV_CLIENT_SECRET")
    )
    NOTION_TOKEN: str = Field(..., validation_alias=AliasChoices("NOTION_TOKEN"))
    GOOGLE_MAP_MCP_PORT: int = Field(
        ..., validation_alias=AliasChoices("GOOGLE_MAP_MCP_PORT")
    )
    GOOGLE_MAP_MCP_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("GOOGLE_MAP_MCP_API_KEY")
    )
    OPENWEATHER_API_KEY: str = Field(
        ..., validation_alias=AliasChoices("OPENWEATHER_API_KEY")
    )

    def show(self):
        console.print(self)

    def get_available_model_deployments(self) -> list[str]:
        return [
            self.AZURE_OPENAI_CHAT_DEPLOYMENT,
            self.AZURE_OPENAI_CHAT_MINI_DEPLOYMENT,
            self.AZURE_OPENAI_REASONING_DEPLOYMENT,
            self.AZURE_OPENAI_REASONING_MINI_DEPLOYMENT,
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


async def init_ms_foundry_monitoring_module():
    """
    import os

    os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
    os.environ["AZURE_TRACING_GEN_AI_CONTENT_RECORDING_ENABLED"] = "true"

    from azure.ai.projects import AIProjectClient
    from azure.identity import AzureCliCredential
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

    OpenAIInstrumentor().instrument()
    project_client = AIProjectClient(
        credential=AzureCliCredential(),
        endpoint=settings.AZURE_AI_FOUNDRY_PROJECT_ENDPOINT,
    )
    configure_azure_monitor(connection_string=project_client.telemetry.get_application_insights_connection_string())
    """
    ...


def init_console() -> Console:
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd")

    args = parser.parse_args()
    if args.cmd == "web-terminal":
        class QueueWriter:
            def __init__(self):
                self.queue = asyncio.Queue()

            def write(self, data: str) -> int:
                # rich가 여러 번 잘라서 쓰기 때문에 빈 문자열은 무시
                if data:
                    self.queue.put_nowait(data)
                return len(data)

            def flush(self) -> None:
                # 콘솔 인터페이스 맞추기용
                pass

        console = Console(file=QueueWriter(), force_terminal=True, color_system="truecolor")
    else:
        console = Console()

    return console


settings = get_settings()
console = init_console()