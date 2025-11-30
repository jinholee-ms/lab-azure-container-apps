import abc
import datetime
import json
from typing import Any
from uuid import uuid4


from langchain.agents import create_agent
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_openai import AzureChatOpenAI
from langchain.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from agents.schema import AgentGraphState, Task
from common import console, settings


class AgentManager:
    def __init__(self):
        self.all_agents: list = []
        
    def get_agent(self, index: int) -> Any:
        return self.all_agents[index]

    def activate_agent(self, index: str) -> None:
        self.all_agents[index].activated = True
        
    def deactivate_agent(self, index: str) -> None:
        self.all_agents[index].activated = False

    def get_activated_agents(self) -> list:
        return [a for a in self.all_agents if a.activated]


agent_manager = AgentManager()


class DebugCallbackHandler(BaseCallbackHandler):
    def on_chat_model_start(self, serialized, messages, **kwargs):
        print("\n=== on_chat_model_start ===")
        print("serialized:", serialized)
        print("messages:")
        for i, msg in enumerate(messages[0]):  # 첫 번째 run 기준
            print(f"[{i}] role={msg.type} | content={msg.content}")
        print("===========================\n")


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
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_deployment=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            #callbacks=[DebugCallbackHandler()],
        )
        self._checkpointer = InMemorySaver()
        self._history_store: dict[str, InMemoryChatMessageHistory] = {}

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
        if include_tools:
            tools = await self.get_tools()
            return self._model.bind_tools(tools)
        return self._model
        
    async def run_langchain_agent(
        self, system_prompt: str, user_prompt: str, session_id: str = uuid4().hex, response_format: Any = None,
    ) -> Any:
        model = await self.get_model()
        if response_format is not None:
            model = model.bind(response_format=response_format)
        response = await create_agent(
            model=model,
            tools=await self.get_tools(),
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
        ).ainvoke(
            {
                "messages": [
                    {"role": "user", "content": user_prompt},
                ],
            },
            config={"configurable": {"thread_id": session_id}},
        )

        return response

    async def run_langgraph_agent(
        self, system_prompt: str, user_prompt: str, session_id: str = uuid4().hex,
    ) -> Any:
        chain = ChatPromptTemplate.from_messages([
        	("system", system_prompt),
            MessagesPlaceholder("history"),
			("human", user_prompt),
		]) | (await self.get_model()).bind_tools(await self.get_tools())

        chain = RunnableWithMessageHistory(
            chain,
            get_session_history=self.get_history,
            history_messages_key="history",
        )
        
        return await chain.ainvoke(
            {},
            config={"configurable": {"session_id": session_id}},
        )

    @staticmethod
    def extract_langchain_agent_answer(answer: Any) -> str:
        if answer is None:
            return "<no answer>"
        if isinstance(answer, str):
            return answer
        # Objects with return_values (AgentFinish etc.)
        if hasattr(answer, "return_values") and isinstance(answer.return_values, dict):
            rv = answer.return_values
            for key in ("output", "final_answer", "answer", "text", "result"):
                if key in rv and rv[key]:
                    return str(rv[key])
            # Fallback join of remaining values
            if rv:
                return " | ".join(f"{k}={v}" for k, v in rv.items())
        # Direct attribute output
        if hasattr(answer, "output"):
            try:
                val = getattr(answer, "output")
                if val:
                    return str(val)
            except Exception:
                pass
        # Dict shape
        if isinstance(answer, dict):
            for key in ("output", "final_answer", "answer", "text", "result"):
                if key in answer and answer[key]:
                    return str(answer[key])
            # Messages list
            if "messages" in answer and isinstance(answer["messages"], list):
                for m in reversed(answer["messages"]):
                    if isinstance(m, AIMessage) or getattr(m, "type", None) in ("ai", "assistant"):
                        content = getattr(m, "content", None) or getattr(m, "text", None)
                        if content:
                            return str(content)
                if answer["messages"]:
                    m = answer["messages"][-1]
                    return str(
                        getattr(m, "content", None)
                        or getattr(m, "text", None)
                        or getattr(m, "message", None)
                        or m
                    )
                return None
            # Intermediate steps (if present)
            if "intermediate_steps" in answer and isinstance(answer["intermediate_steps"], list):
                try:
                    return json.dumps(answer, ensure_ascii=False, indent=2)
                except Exception:
                    pass
            # Generic JSON dump fallback
            try:
                return json.dumps(answer, ensure_ascii=False, indent=2)
            except Exception:
                return repr(answer)
        # List of messages directly
        if isinstance(answer, list):
            parts = []
            for m in answer:
                if isinstance(m, str):
                    parts.append(m)
                elif isinstance(m, dict):
                    parts.append(str(m.get("content") or m.get("text") or m))
                else:
                    parts.append(getattr(m, "content", getattr(m, "text", repr(m))))
            if parts:
                return "\n".join(parts)
        # Last resort
        try:
            return json.dumps(answer, ensure_ascii=False, indent=2)
        except Exception:
            return repr(answer)

class TaskOperator:
    def __init__(self, agent: AgentBase) -> None:
        self.agent = agent

    async def run_node(self, state: AgentGraphState) -> str:
        with console.status(f"[grey] {self.agent.name} is processing...[/]", spinner="arc"):
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
    async def exec(self, state: AgentGraphState, task: Task = None, previous_tasks: list[Task] = None) -> None:
        raise NotImplementedError()