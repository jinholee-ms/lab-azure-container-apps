import datetime
import httpx
from pathlib import Path

from langchain_core.tools import tool
from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphState, Task
from capabilities.mcp import get_mcp_client
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
    async def exec(self, state: AgentGraphState, task: Task = None, previous_tasks: list[Task] = None) -> None:
        response = await self.agent.run_langchain_agent(
            self.agent.generate_system_prompt(),
            self.agent.generate_user_prompt(question=task.question),
            session_id=state.session_id,
        )
        
        task.answer = self.agent.extract_langchain_agent_answer(response)


class WeatherAgent(AgentBase):
    name: str = "WeatherAgent"
    description: str = "실시간 날씨 정보 조회를 담당하는 에이전트"
    activated: bool = True
    locked: bool = False
    task_operator = WeatherOperator

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "weather_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)
        
    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "weather_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)
    
    async def get_tools(self) -> list[callable]:
        return [get_current_weather, get_forecast]
