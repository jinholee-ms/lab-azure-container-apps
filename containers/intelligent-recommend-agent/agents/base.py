import abc
import json
from typing import Any
from uuid import uuid4

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AIMessage, AgentFinish
from rich.panel import Panel
from rich.syntax import Syntax

from agents.schema import AgentGraphStateBase, AgentProfile
from common import console, settings


class AgentManager:
    def __init__(self):
        self.all_agents: list = []

    def get_agent(self, index: int) -> Any:
        return self.all_agents[index]


agent_manager = AgentManager()


class DebugCallbackHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        console.log("[yellow]Serialized Info[/yellow]")
        serialized_pretty = json.dumps(serialized, indent=2, ensure_ascii=False)
        console.log(Panel(serialized_pretty, style="dim"))

        console.log("\n[yellow]Prompts[/yellow]")
        for idx, prompt in enumerate(prompts):
            console.log(f"[green]Prompt #{idx}[/green]")
            syntax = Syntax(prompt, "markdown", theme="ansi_dark", line_numbers=False)
            console.log(Panel(syntax, style="dim"))

        console.rule("[bold cyan]End LLM Start[/bold cyan]\n")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        console.rule("[bold cyan]LLM End[/bold cyan]")

        console.print("[bold yellow]Response[/bold yellow]")
        response_pretty = json.dumps(response, indent=2, ensure_ascii=False)
        console.print(Panel(response_pretty, style="dim"))

        console.rule("[bold cyan]End LLM End[/bold cyan]\n")


class AgentBaseMeta(type):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        if name != "AgentBase":
            agent_manager.all_agents.append(new_class)
        return new_class


class AgentBase(metaclass=AgentBaseMeta):
    profile: AgentProfile

    def __init__(self, session_id: str = None) -> None:
        self.session_id = session_id if session_id else uuid4().hex
        self.history: InMemoryChatMessageHistory = InMemoryChatMessageHistory()

    async def initialize(
        self,
        deployment_name: str = None,
        response_format: Any = None,
        system_prompt_kwargs: dict = {},
    ) -> None:
        kwargs = {
            "azure_endpoint": settings.AZURE_OPENAI_ENDPOINT,
            "openai_api_key": settings.AZURE_OPENAI_API_KEY,
            "openai_api_version": settings.AZURE_OPENAI_API_VERSION,
        }
        if deployment_name:
            kwargs["deployment_name"] = deployment_name
        else:
            kwargs["deployment_name"] = self.profile.deployment_name
        if response_format:
            kwargs["model_kwargs"] = {"response_format": response_format}
        if self.profile.enable_debugging:
            kwargs["callbacks"] = [DebugCallbackHandler()]

        self.model = AzureChatOpenAI(**kwargs)

        self.system_prompt = self.generate_system_prompt(**system_prompt_kwargs)

        if tools := await self.get_tools():
            self.agent: AgentExecutor = AgentExecutor(
                agent=create_openai_tools_agent(
                    self.model,
                    tools=tools,
                    prompt=self.get_chat_prompt_template(additional_messages=[MessagesPlaceholder("agent_scratchpad")]),
                ),
                tools=tools,
                # verbose=enable_debugging or False,
            )
        else:
            self.agent = self.get_chat_prompt_template() | self.model

    async def run(self, user_prompt: str) -> Any:
        chain = RunnableWithMessageHistory(
            self.agent,
            self.get_history_store,
            input_messages_key="input",
            history_messages_key="history",
        )

        return await chain.ainvoke(
            {"input": user_prompt},
            config={"configurable": {"session_id": self.session_id}}
        )

    @abc.abstractmethod
    def generate_system_prompt(self, **kwargs) -> str:
        return ""

    @abc.abstractmethod
    def generate_user_prompt(self, **kwargs) -> str:
        return ""

    @abc.abstractmethod
    async def get_tools(self) -> list[callable]:
        return []

    def get_chat_prompt_template(self, additional_messages: list = None) -> ChatPromptTemplate:
        messages = [
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
        if additional_messages:
            messages.extend(additional_messages)

        return ChatPromptTemplate.from_messages(messages)

    def get_history_store(self, session_id: str) -> InMemoryChatMessageHistory:
        return self.history

    @staticmethod
    def extract_answer(answer: Any) -> str:
        # 1) answer가 LangChain 메시지 리스트로 들어온 경우
        if isinstance(answer, list):
            ai_messages = [m for m in answer if isinstance(m, AIMessage)]
            if ai_messages:
                return ai_messages[-1].content  # 마지막 AIMessage만 리턴
            # 혹시 AIMessage가 없다면 마지막 요소를 문자열로
            return str(answer[-1])

        # 2) answer가 dict 구조인 경우 (LangGraph 응답 형태)
        if isinstance(answer, dict):
            # history 안에 AIMessage가 있는 경우
            if "history" in answer and isinstance(answer["history"], list):
                ai_messages = [m for m in answer["history"] if isinstance(m, AIMessage)]
                if ai_messages:
                    return ai_messages[-1].content
            # "response" 키가 JSON 문자열일 수 있음
            if "response" in answer:
                return answer["response"]
            # 그 외 일반 dict 처리
            for key in ("output", "final_answer", "answer", "text", "result"):
                if key in answer:
                    return str(answer[key])

        if isinstance(answer, AgentFinish):
            return str(answer.return_values.get("output", ""))
        elif isinstance(answer, AIMessage):
            return answer.content
        elif isinstance(answer, str):
            return answer
        return str(answer)


class TaskOperator:
    def __init__(self, agent: AgentBase) -> None:
        self.agent = agent

    async def run_node(self, state: AgentGraphStateBase) -> str:
        with console.status(f"[blue] {self.agent.profile.name} is processing...[/]"):
            start_time = console.timer()
            await self.exec(state)
            end_time = console.timer()
        console.log(f"[green] ✅ ({end_time - start_time:.2f}s) {self.agent.profile.name} is completed. [/]")
        return state

    @abc.abstractmethod
    async def exec(self, state: AgentGraphStateBase) -> None:
        raise NotImplementedError()