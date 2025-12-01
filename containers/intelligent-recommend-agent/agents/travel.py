import datetime
from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphState, Task
from capabilities.mcp import get_mcp_client
from common import console


class TravelOperator(TaskOperator):
    async def exec(
        self,
        state: AgentGraphState,
        task: Task = None,
        previous_tasks: list[Task] = None,
    ) -> None:
        sanitized_tasks = []
        if previous_tasks:
            for index, t in enumerate(previous_tasks):
                sanitized_tasks.append(
                    {
                        "index": index,
                        "agent": t.agent,
                        "input": t.question,
                        "output": t.answer,
                    }
                )

        response = await self.agent.run_langchain_agent(
            self.agent.generate_system_prompt(),
            self.agent.generate_user_prompt(
                question=task.question,
                tasks=sanitized_tasks,
            ),
            session_id=state.session_id,
        )

        task.answer = self.agent.extract_langchain_agent_answer(response)


class TravelAgent(AgentBase):
    name: str = "TravelAgent"
    description: str = (
        "여행 관련 정보 수집 및 예약 (호텔, 항공권, 액티비티, 레스토랑 등)을 담당하는 에이전트"
    )
    activated: bool = True
    locked: bool = False
    task_operator = TravelOperator

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    async def get_tools(self) -> list[callable]:
        return await get_mcp_client().get_tools(server_name="google-places")
