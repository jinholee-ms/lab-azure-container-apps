from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile
from capabilities.mcp import get_mcp_client


class TravelRecommendOperator(TaskOperator):
    async def exec(self, state: AgentGraphStateBase) -> None:
        await self.agent.initialize(enable_debugging=True)
        response = await self.agent.run(
            self.agent.generate_user_prompt(
                itinerary_suggestion=state.context.itinerary_suggestion,
                profile=state.context.profile,
            ),
        )
        state.context.recommendations = self.agent.extract_answer(response)


class TravelRecommendAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="TravelRecommendAgent",
        description="여행 관련 정보 수집 및 예약 (호텔, 항공권, 액티비티, 레스토랑 등)을 담당하는 에이전트",
        task_operator=TravelRecommendOperator,
    )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_recommend_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_recommend_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    async def get_tools(self) -> list[callable]:
        return await get_mcp_client().get_tools(server_name="google-places")
