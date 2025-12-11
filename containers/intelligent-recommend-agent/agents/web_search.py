from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile
from capabilities.mcp import get_mcp_client


class WebSearchOperator(TaskOperator):
    async def exec(self, state: AgentGraphStateBase) -> None:
        self.agent.initialize()
        response = await self.agent.run(
            self.agent.generate_user_prompt(question=state.question),
        )
        state.answer = self.agent.extract_answer(response)


class WebSearchAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="WebSearchAgent",
        description="웹 검색을 담당하는 에이전트",
        task_operator=WebSearchOperator,
    )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "web_search_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "web_search_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    async def get_tools(self) -> list[callable]:
        return await get_mcp_client().get_tools(server_name="naver-web")
