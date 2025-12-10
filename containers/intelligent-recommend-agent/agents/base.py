import abc
import datetime
from typing import Any
from uuid import uuid4

from langchain.agents import initialize_agent, AgentType
from langchain.callbacks.base import BaseCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain.chains.conversation.base import ConversationChain
from langchain_openai import AzureChatOpenAI
from langchain.schema import AIMessage, SystemMessage, HumanMessage, AgentFinish, BaseMessage

from agents.schema import AgentGraphState, Task
from common import console, settings


# 기존 AgentManager 코드는 그대로 유지 (LangChain 의존성 없음)
class AgentManager:
    def __init__(self):
        self.all_agents: list = []

    async def initialize_agents(self) -> None:
        for agent in self.all_agents:
            await agent.initialize()

    def get_agent(self, index: int) -> Any:
        return self.all_agents[index]

    def activate_agent(self, index: int) -> None:
        self.all_agents[index].activated = True

    def deactivate_agent(self, index: int) -> None:
        self.all_agents[index].activated = False

    def create_agent(self, index: int) -> None:
        self.all_agents[index].created = True

    def get_activated_agents(self) -> list:
        return [a for a in self.all_agents if a.activated]


agent_manager = AgentManager()


class DebugCallbackHandler(BaseCallbackHandler):
    # 0.x 버전에서는 on_chat_model_start 대신 on_llm_start를 사용하거나,
    # 해당 메서드의 인자를 0.x 형식에 맞춰 수정해야 함
    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        console.log("serialized:", serialized)
        console.log("prompts:")
        for i, prompt in enumerate(prompts):
            console.log(f"[{i}] prompt={prompt}")

    # 0.x에서 on_chat_model_start 대신 on_llm_start로 변경하는 것이 일반적이지만,
    # 1.x 스타일의 콜백이 필요한 경우를 위해 원본을 주석 처리하고 0.x에 맞는 메서드를 추가하는 것이 안전합니다.
    # def on_chat_model_start(self, serialized, messages, **kwargs):
    #     print("\n=== on_chat_model_start ===")
    #     ...


class AgentBaseMeta(type):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        if name != "AgentBase":
            agent_manager.all_agents.append(new_class())
        return new_class


class AgentBase(metaclass=AgentBaseMeta):
    name: str = None
    description: str = None
    activated: bool = False
    locked: bool = False
    task_operator: "TaskOperator" = None

    def __init__(self):
        self._model = AzureChatOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            openai_api_key=settings.AZURE_OPENAI_API_KEY,
            deployment_name=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            openai_api_version=settings.AZURE_OPENAI_API_VERSION,
            callbacks=[DebugCallbackHandler()],
        )
        self._history_store: dict[str, InMemoryChatMessageHistory] = {}

    async def initialize(self) -> None:
        pass

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in self._history_store:
            self._history_store[session_id] = InMemoryChatMessageHistory()
        return self._history_store[session_id]

    @abc.abstractmethod
    def generate_system_prompt(self, **kwargs) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def generate_user_prompt(self, **kwargs) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_tools(self) -> list[callable]:
        return []

    async def get_model(self, include_tools: bool = True) -> AzureChatOpenAI:
        # 0.x 버전에는 .bind_tools() 메서드가 없으며, 도구는 initialize_agent에서 통합됩니다.
        # 이 메서드는 단순히 모델 객체를 반환합니다.
        return self._model

    async def run_langchain_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        session_id: str = uuid4().hex,
        response_format: Any = None, # 0.x Agent는 response_format을 직접 지원하지 않음
    ) -> Any:
        # 1. session 별 history 가져오기
        history = self.get_history(session_id)

        # 2. response_format 여부에 따라 사용할 LLM 결정
        if response_format is not None:
            # 호출마다 다른 response_format 을 쓰고 싶을 때
            llm = AzureChatOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                openai_api_key=settings.AZURE_OPENAI_API_KEY,
                deployment_name=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                openai_api_version=settings.AZURE_OPENAI_API_VERSION,
                model_kwargs={
                    "response_format": response_format,
                },
                callbacks=[DebugCallbackHandler()],
            )
        else:
            # 평소 쓰던 기본 모델
            llm = self._model

        # 3. history 를 메모리로 감싸기 (ConversationChain 은 BaseMemory 를 기대)
        memory = ConversationBufferMemory(
            chat_memory=history,
            memory_key="history",   # 템플릿에서 쓰일 key 이름
            return_messages=True,
        )

        # 4. ConversationChain 설정
        chain = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=False,
        )

        # 5. 시스템 프롬프트 + 유저 프롬프트 합치기
        full_input = f"{system_prompt}\n\n{user_prompt}"

        # 6. JSON mode 가 걸린 llm 로 호출
        return await chain.arun(input=full_input)

    async def run_langgraph_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        session_id: str = uuid4().hex,
    ) -> Any:
        # 0.x 버전에서는 LangGraph를 사용할 수 없으며, ConversationChain을 사용해야 합니다.
        # LangGraph 코드를 ConversationChain 코드로 대체합니다.
        
        # 1. 메모리 생성 (history 객체를 래핑)
        history = self.get_history(session_id)
        
        # 2. ConversationChain 설정 (0.x의 표준 대화 관리 방법)
        chain = ConversationChain(
            llm=self._model,
            memory=history, # history 객체를 메모리 인자로 직접 전달
            verbose=False, # 디버깅 시 True로 설정
        )
        
        # 3. 시스템 프롬프트를 포함한 사용자 입력 구성
        # 0.x ConversationChain은 시스템 프롬프트가 기본 템플릿에 통합되어 있지 않으므로,
        # 프롬프트를 직접 커스터마이징해야 하지만, 여기서는 단순화를 위해 input에 추가합니다.
        
        full_input = f"{system_prompt}\n\n{user_prompt}"

        return await chain.arun(input=full_input)

    @staticmethod
    def extract_langchain_agent_answer(answer: Any) -> str:
        # 0.x 버전의 Agent 실행 결과는 대부분 딕셔너리 또는 AgentFinish 객체입니다.
        if answer is None:
            return "<no answer>"
        if isinstance(answer, str):
            return answer
        
        # 0.x Agent 실행 결과 (딕셔너리)
        if isinstance(answer, dict):
            # 'output' 키는 Agent Executor의 최종 결과입니다.
            if "output" in answer:
                return str(answer["output"])
            # 그 외 딕셔너리에서 적절한 답변 추출 시도
            for key in ("final_answer", "answer", "text", "result"):
                if key in answer and answer[key]:
                    return str(answer[key])
        
        # 0.x AgentFinish 객체
        if isinstance(answer, AgentFinish):
            return str(answer.return_values.get("output", "AgentFinish without explicit output"))

        # 기존의 복잡한 추출 로직을 최대한 유지하지만, 0.x 결과 형식에 초점을 맞춥니다.
        # (나머지 로직은 1.x 스타일의 결과를 처리하기 위한 부분이 많으므로,
        #  일단 0.x에서 가장 흔한 Dict/AgentFinish 형태 처리에 집중했습니다.)

        return str(answer) # 마지막 수단으로 문자열로 변환

# TaskOperator 코드는 그대로 유지 (LangChain 의존성 없음)
class TaskOperator:
    def __init__(self, agent: AgentBase) -> None:
        self.agent = agent

    async def run_node(self, state: AgentGraphState) -> str:
        with console.status(
            f"[blue] {self.agent.name} is processing...[/]", spinner="aesthetic"
        ):
            if (workflow := state.workflow) and (task := workflow.get_next_task()):
                task.started_at = datetime.datetime.now(datetime.UTC)

                if task.use_answers_from:
                    previous_tasks = [workflow.tasks[i] for i in task.use_answers_from]
                else:
                    previous_tasks = None
                await self.exec(state, task=task, previous_tasks=previous_tasks)

                task.finished_at = datetime.datetime.now(datetime.UTC)
            else:
                await self.exec(state)

        return state

    @abc.abstractmethod
    async def exec(
        self,
        state: AgentGraphState,
        task: Task = None,
        previous_tasks: list[Task] = None,
    ) -> None:
        raise NotImplementedError()