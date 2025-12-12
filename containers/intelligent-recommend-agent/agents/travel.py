from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile, TravelAgentContext
from agents.travel_itinerary_suggestion import TravelItinerarySuggestionAgent
from agents.travel_profile import TravelProfileAgent
from agents.travel_recommend import TravelRecommendAgent
from agents.travel_summary import TravelSummaryAgent
from common import console


class TravelAgentGraph:
    def __init__(self, session_id: str = None) -> None:
        self.session_id: str = uuid4().hex if not session_id else session_id
        self.sub_agents = [
            ("TravelProfileAgent", TravelProfileAgent),
            ("TravelItinerarySuggestionAgent", TravelItinerarySuggestionAgent),
            ("TravelRecommendAgent", TravelRecommendAgent),
            ("TravelSummaryAgent", TravelSummaryAgent),
        ]
        self.graph = self.build()

    def build(self) -> CompiledStateGraph:
        graph = StateGraph(AgentGraphStateBase)

        for name, agent_cls in self.sub_agents:
            task_operator = agent_cls.profile.task_operator(agent_cls(self.session_id))
            graph.add_node(name, task_operator.run_node)

        graph.set_entry_point("TravelProfileAgent")

        graph.add_edge("TravelProfileAgent", "TravelItinerarySuggestionAgent")
        graph.add_edge("TravelItinerarySuggestionAgent", "TravelRecommendAgent")
        graph.add_edge("TravelRecommendAgent", "TravelSummaryAgent")
        graph.add_edge("TravelSummaryAgent", END)

        compiled = graph.compile()
        console.log("🛠️ TravelAgent graph compiled successfully.")
        console.log(compiled.get_graph().draw_ascii(), style="dim")

        return compiled

    async def run(self, question: str) -> str:
        response = await self.graph.ainvoke(
            AgentGraphStateBase(context=TravelAgentContext(), question=question)
        )
        return response.get("answer")


class TravelOperator(TaskOperator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = TravelAgentGraph()

    async def exec(self, state: AgentGraphStateBase) -> None:
        response = await self.graph.run(state.question)
        state.answer = response


class TravelAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="TravelAgent",
        description="사용자의 여행 계획을 도와주는 에이전트입니다. 여행 일정, 도시, 인원 정보가 필요합니다.",
        task_operator=TravelOperator,
    )