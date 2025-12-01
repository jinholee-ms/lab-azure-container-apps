from uuid import uuid4

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.base import agent_manager
from agents.schema import AgentGraphState, AgentGraphInput
from agents.planning import PlanningAgent
from agents.summary import SummaryAgent
from common import console


class Orchestrator:
    def __init__(self) -> None:
        self.session_id: str = uuid4().hex

    def route_agent_flow(self, state: AgentGraphState) -> AgentGraphState:
        return state

    def route_conditional_loopback(self, state: AgentGraphState) -> AgentGraphState:
        if task := state.workflow.get_next_task():
            return task.agent
        else:
            return "finalize"

    def finalize(self, state: AgentGraphState) -> AgentGraphState:
        task = state.workflow.get_last_task()
        state.answer = task.answer
        return state

    def build(self) -> CompiledStateGraph:
        agents = agent_manager.get_activated_agents()
        operators = [agent.task_operator(agent) for agent in agents]

        graph = StateGraph(AgentGraphState)
        graph.add_node("route_agent_flow", self.route_agent_flow)
        graph.add_node("finalize", self.finalize)
        for operator in operators:
            graph.add_node(operator.agent.name, operator.run_node)

        graph.add_edge("finalize", END)
        for operator in operators:
            graph.add_edge(operator.agent.name, "route_agent_flow")
        path = {
            operator.agent.name: operator.agent.name
            for operator in operators
            if not isinstance(operator.agent, PlanningAgent)
        }
        path["finalize"] = "finalize"
        graph.add_conditional_edges(
            "route_agent_flow",
            self.route_conditional_loopback,
            path,
        )

        graph.set_entry_point(PlanningAgent.name)

        compiled = graph.compile()
        console.log("🛠️  Orchestrator graph compiled successfully.")
        console.log(compiled.get_graph().draw_ascii())

        return compiled

    async def run(self, question: str) -> str:
        graph = self.build()
        response = await graph.ainvoke(
            AgentGraphState(
                session_id=self.session_id,
                input=AgentGraphInput(
                    question=question,
                    agents=[agent for agent in agent_manager.get_activated_agents()]
                    + [SummaryAgent],
                ),
            )
        )
        return response.get("answer")
