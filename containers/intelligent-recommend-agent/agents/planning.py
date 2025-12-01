import json
from pathlib import Path
from textwrap import dedent

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from rich.table import Table

from agents.base import AgentBase, TaskOperator
from agents.schema import PlanningStepsArgument, AgentGraphState, Task, Workflow
from common import console


@tool(
    "plan",
    description=dedent(
        """
        Returns a structured execution plan based on the user's request.

        Each step should have:
        - title: short title of the step
        - description: what to do in this step
        - agent: which agent or tool to call
        - question: question or input for this step
	"""
    ),
    args_schema=PlanningStepsArgument,
)
async def plan(steps: list) -> PlanningStepsArgument:
    # 실제 실행은 안 쓰이고, LLM tool-call schema 용도로만 사용된다고 보면 됨.
    return PlanningStepsArgument(steps=steps)


class PlanningOperator(TaskOperator):
    async def exec(
        self,
        state: AgentGraphState,
        task: Task = None,
        previous_tasks: list[Task] = None,
    ) -> None:
        # model = (await self.agent.get_model(include_tools=False)).with_structured_output(PlanningStepsArgument)
        response = await self.agent.run_langchain_agent(
            self.agent.generate_system_prompt(agents=state.input.agents),
            self.agent.generate_user_prompt(question=state.input.question),
            session_id=state.session_id,
            response_format=PlanningStepsArgument,
        )

        answer = self.agent.extract_langchain_agent_answer(response)
        if steps := json.loads(answer).get("steps"):
            state.workflow = Workflow(tasks=[Task(**step) for step in steps])

            table = Table(
                title="📝 [PlanningAgent] Generated workflow.", show_lines=False
            )
            table.add_column("#", style="cyan", justify="right")
            table.add_column("Agent", style="magenta")
            table.add_column("Question", style="green")
            table.add_column("ReferTo", style="cyan")
            for idx, task in enumerate(state.workflow.tasks):
                table.add_row(
                    str(idx),
                    task.agent,
                    task.question,
                    "".join([str(i) for i in task.use_answers_from]),
                )
            console.print(table)
        else:
            console.log(f"⚠️ [PlanningAgent] No steps found in the generated plan.")
            return


class PlanningAgent(AgentBase):
    name: str = "PlanningAgent"
    description: str = (
        "사용자의 요청을 여러 개의 단계(step)로 분해하여, 정의된 에이전트들이 실행할 수 있는 Plan을 만드는 에이전트"
    )
    activated: bool = True
    locked: bool = True
    task_operator = PlanningOperator

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "planning_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "planning_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    async def get_tools(self) -> list[callable]:
        return []
