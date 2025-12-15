from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import PlannedAgentGraphState, AgentProfile, AgentPrompt, PromptVariable


class TravelSummaryOperator(TaskOperator):
    async def exec(self, state: PlannedAgentGraphState) -> None:
        await self.agent.initialize()
        response = await self.agent.run(
            self.agent.generate_user_prompt(
                itinerary_suggestion=state.context.itinerary_suggestion,
                profile=state.context.profile,
                recommendations=state.context.recommendations,
            ),
        )

        state.answer = self.agent.extract_answer(response)


class TravelSummaryAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="TravelSummaryAgent",
        description="사용자의 요청에 대해 여러 에이전트가 수행한 작업 결과를 요약하는 에이전트",
        task_operator=TravelSummaryOperator,
        interactive=False,
        prompts=AgentPrompt(
            system=[
                PromptVariable(
                    type="default",
                    filename="travel_summary_system_prompt.jinja",
                    selected=True,
                ),
            ],
            user=[
                PromptVariable(
                    type="default",
                    filename="travel_summary_human_prompt.jinja",
                    selected=True,
                ),
            ],
        ),
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
