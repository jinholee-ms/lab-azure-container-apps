import datetime
from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphState, Task
from common import console


class SummaryOperator(TaskOperator):
    async def exec(
        self,
        state: AgentGraphState,
        task: Task = None,
        previous_tasks: list[Task] = None,
    ) -> None:
        agents = {}
        for task in state.workflow.tasks:
            if not task.finished_at:
                break
            if task.agent not in agents:
                agents[task.agent] = []
            agents[task.agent].append(task.answer)

        response = await self.agent.run_langchain_agent(
            self.agent.generate_system_prompt(),
            self.agent.generate_user_prompt(question=task.question, agents=agents),
            session_id=state.session_id,
        )

        task.answer = self.agent.extract_langchain_agent_answer(response)


class SummaryAgent(AgentBase):
    name: str = "SummaryAgent"
    description: str = (
        "사용자의 요청에 대해 여러 에이전트가 수행한 작업 결과를 요약하는 에이전트"
    )
    activated: bool = True
    locked: bool = True
    task_operator = SummaryOperator

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "summary_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "summary_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)
