import json
from pathlib import Path
from uuid import uuid4

from langchain_core.prompts import PromptTemplate
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.base import AgentBase, TaskOperator
from agents.chatbot import ChatbotAgent
from agents.travel import TravelAgent
from agents.schema import AgentGraphStateBase, AgentProfile, TriageAgentContext, TriageAgentOutput
from common import console


class TriageAgentGraph:
    def __init__(self, session_id: str = None) -> None:
        self.session_id: str = uuid4().hex if not session_id else session_id
        self.sub_agents = [
            ("TriageAgent", TriageAgent),
            ("TravelAgent", TravelAgent),
            ("ChatbotAgent", ChatbotAgent),
        ]
        self.graph = self.build()

    def route_conditional_loopback(self, state: AgentGraphStateBase) -> str:
        if state.context.selected_agent_name:
            return state.context.selected_agent_name
        return "finalize"

    def build(self) -> CompiledStateGraph:
        graph = StateGraph(AgentGraphStateBase)

        for name, agent_cls in self.sub_agents:
            task_operator = agent_cls.profile.task_operator(agent_cls(self.session_id))
            graph.add_node(name, task_operator.run_node)

        graph.set_entry_point("TriageAgent")

        graph.add_conditional_edges(
            "TriageAgent",
            self.route_conditional_loopback,
            {
                "TravelAgent": "TravelAgent",
                "ChatbotAgent": "ChatbotAgent",
                "finalize": END,
            },
        )
        graph.add_edge("TravelAgent", END)
        graph.add_edge("ChatbotAgent", END)

        compiled = graph.compile()
        console.log("🛠️ TriageAgent graph compiled successfully.")
        console.log(compiled.get_graph().draw_ascii())

        return compiled

    async def run(self, question: str) -> str:
        response = await self.graph.ainvoke(
            AgentGraphStateBase(
                question=question, context=TriageAgentContext(),
            ),
        )
        return response.get("answer")


class TriageOperator(TaskOperator):
    async def exec(self, state: AgentGraphStateBase) -> None:
        await self.agent.initialize(
            response_format=TriageAgentOutput,
            system_prompt_kwargs={
                "agents": [
                    {"name": ChatbotAgent.profile.name, "description": ChatbotAgent.profile.description},
                    {"name": TravelAgent.profile.name, "description": TravelAgent.profile.description},
                ]
            }
        )

        response = await self.agent.run(
            self.agent.generate_user_prompt(question=state.question),
        )

        answer = self.agent.extract_answer(response)
        if answer := json.loads(answer):
            if answer["action"] == "route":
                state.context.selected_agent_name = answer["agent"]
            elif answer["action"] == "clarify":
                state.answer = answer["question"]
        else:
            console.log(f"⚠️ No agent found in the TriageOperator")


class TriageAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="TriageAgent",
        description="사용자의 에이전트 요청을 분석하고, 적절한 하위 에이전트 (여행 에이전트 또는 챗봇 에이전트) 로 라우팅하는 에이전트",
        task_operator=TriageOperator,
        chat_in_settings=False,
    )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "triage_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "triage_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)