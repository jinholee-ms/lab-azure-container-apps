from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile


class ChatbotOperator(TaskOperator):
    async def exec(self, state: AgentGraphStateBase) -> None:
        await self.agent.initialize()
        response = await self.agent.run(state.question)
        state.answer = self.agent.extract_answer(response)


class ChatbotAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="ChatbotAgent",
        description="단순 인사, 잡담, 일반 지식 질문, 설명 요청 등 범용 대화에 답변하는 에이전트",
        task_operator=ChatbotOperator,
    )