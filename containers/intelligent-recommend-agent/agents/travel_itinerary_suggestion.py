from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile


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
    )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_itinerary_suggestion_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_itinerary_suggestion_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)