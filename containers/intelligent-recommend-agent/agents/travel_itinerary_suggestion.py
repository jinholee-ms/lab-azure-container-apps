from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile, AgentPrompt, PromptVariable
from capabilities.mcp import get_mcp_client
from capabilities.tools import get_current_weather, get_forecast
from common import settings


class TravelItinerarySuggestionOperator(TaskOperator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def exec(self, state: AgentGraphStateBase) -> None:
        await self.agent.initialize()
        response = await self.agent.run(
            self.agent.generate_user_prompt(
                itinerary_request=state.question,
                profile=state.context.profile,
            ),
        )
        state.context.itinerary_suggestion = self.agent.extract_answer(response)


class TravelItinerarySuggestionAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="TravelItinerarySuggestionAgent",
        description="사용자의 여행 프로필, 여행 목적,同行 인원 구성, 도시 정보, 체류 기간을 기반으로 가장 최적화된 여행 일정을 설계하는 전문 AI 플래너",
        task_operator=TravelItinerarySuggestionOperator,
        prompts=AgentPrompt(
            system=[
                PromptVariable(
                    type="version_001",
                    filename="travel_itinerary_suggestion_system_prompt_001.jinja",
                ),
                PromptVariable(
                    type="version_002",
                    filename="travel_itinerary_suggestion_system_prompt_002.jinja",
                    selected=True,
                ),
            ],
            user=[
                PromptVariable(
                    type="default",
                    filename="travel_itinerary_suggestion_human_prompt.jinja",
                    selected=True,
                ),
            ],
        ),
        enable_debugging=True,
    )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / self.profile.prompts.get_selected_prompt("system").filename,
            template_format="jinja2",
            encoding="utf-8",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / self.profile.prompts.get_selected_prompt("user").filename,
            template_format="jinja2",
            encoding="utf-8",
        ).format(**kwargs)

    async def get_tools(self) -> list:
        tools = await get_mcp_client().get_tools(server_name="naver-web")
        tools.extend([get_current_weather, get_forecast])
        return tools