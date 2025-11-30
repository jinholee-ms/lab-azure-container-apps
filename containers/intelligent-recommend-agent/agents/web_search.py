import datetime
from pathlib import Path

from langchain_core.prompts import PromptTemplate

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphState, Task
from capabilities.mcp import get_mcp_client


class WebSearchOperator(TaskOperator):
    async def exec(self, state: AgentGraphState, task: Task = None, previous_tasks: list[Task] = None) -> None:
        response = await self.agent.run_langchain_agent(
            self.agent.generate_system_prompt(),
            self.agent.generate_user_prompt(question=task.question),
            session_id=state.session_id,
        )
        
        task.answer = self.agent.extract_langchain_agent_answer(response)


class WebSearchAgent(AgentBase):
    name: str = "WebSearchAgent"
    description: str = "웹 검색을 담당하는 에이전트"
    activated: bool = True
    locked: bool = False
    task_operator = WebSearchOperator

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
