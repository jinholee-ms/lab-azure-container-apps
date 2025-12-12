import httpx
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile, AgentPrompt, PromptVariable
from common import settings


BASE_URL = "https://api.openweathermap.org/data/2.5"


@tool
async def get_current_weather(city: str, units: str = "metric") -> dict:
    """
    Get current weather for a given city.

    Args:
        city (str): City name (e.g., "Seoul")
        units (str): metric, imperial, or standard
    """

    async with httpx.AsyncClient(timeout=10) as client:
        params = {
            "q": city,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": units,
        }
        r = await client.get(f"{BASE_URL}/weather", params=params)
        r.raise_for_status()
        return r.json()


@tool
async def get_forecast(city: str, units: str = "metric") -> dict:
    """
    Get 5-day / 3-hour interval forecast for a given city.

    Args:
        city (str): City name
        units (str): metric, imperial, standard
    """
    async with httpx.AsyncClient(timeout=10) as client:
        params = {
            "q": city,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": units,
        }
        r = await client.get(f"{BASE_URL}/forecast", params=params)
        r.raise_for_status()
        return r.json()


class WeatherOperator(TaskOperator):
    async def exec(self, state: AgentGraphStateBase) -> None:
        await self.agent.initialize()
        response = await self.agent.run(
            self.agent.generate_user_prompt(question=state.question),
        )
        state.answer = self.agent.extract_answer(response)


class WeatherAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="WeatherAgent",
        description="실시간 날씨 정보 조회를 담당하는 에이전트",
        task_operator=WeatherOperator,
        prompts=AgentPrompt(
            system=[
                PromptVariable(
                    type="default",
                    filename="weather_system_prompt.jinja",
                    selected=True,
                ),
            ],
            user=[
                PromptVariable(
                    type="default",
                    filename="weather_human_prompt.jinja",
                    selected=True,
                ),
            ],
        ),
    )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / self.profile.prompts.get_selected_prompt("system").filename,
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / self.profile.prompts.get_selected_prompt("user").filename,
            template_format="jinja2",
        ).format(**kwargs)

    async def get_tools(self) -> list[callable]:
        return [get_current_weather, get_forecast]
