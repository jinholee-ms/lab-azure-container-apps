from datetime import datetime
import os
from pathlib import Path
import subprocess

from langchain_community.agent_toolkits.sql.base import SQLDatabaseToolkit
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import PromptTemplate
import pandas as pd

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphStateBase, AgentProfile, AgentPrompt, PromptVariable
from capabilities.db import ReadOnlySQLDatabase
from capabilities.graphrag import GraphRAG
from common import console


@tool(
    "get_travel_profile_from_graphrag",
    description="사용자의 여행 활동, 호텔 방문 기록, 선호도, 리뷰 히스토리를 기반으로 개인화된 여행 프로필을 구성하는데 필요한 정보를 Graphrag에서 검색합니다.",
)
async def get_travel_profile_from_graphrag(question: str) -> str:
    return await TravelProfileAgent.graphrag.retrieve_on_global(question)


class TravelProfileOperator(TaskOperator):
    async def exec(self, state: AgentGraphStateBase) -> None:
        await self.agent.initialize()
        response = await self.agent.run(self.agent.generate_user_prompt(question=state.question))
        state.context.profile = self.agent.extract_answer(response)


class TravelSQLToolkit(SQLDatabaseToolkit):
    def get_tools(self):
        tools = super().get_tools()
        tools.append(get_travel_profile_from_graphrag)
        return tools


class TravelProfileAgent(AgentBase):
    profile: AgentProfile = AgentProfile(
        name="TravelProfileAgent",
        description=(
            "사용자의 여행 활동, 호텔 방문 기록, 선호도, 리뷰 히스토리를 기반으로 개인화된 여행 프로필을 구성하고, "
            "다른 에이전트 사용할 수 있는 관련 정보 (추천 호텔, 선호 지역, 여행 패턴 등) 을 제공하는 에이전트"
        ),
        task_operator=TravelProfileOperator,
        prompts=AgentPrompt(
            system=[
                PromptVariable(
                    type="default",
                    filename="travel_profile_system_prompt.jinja",
                    selected=True,
                ),
            ],
            user=[
                PromptVariable(
                    type="default",
                    filename="travel_profile_human_prompt.jinja",
                    selected=True,
                ),
            ],
        ),
        enable_debugging=True,
    )

    assets = [
        ("./assets/hotels.csv", "Hotels"),
        ("./assets/user_hotel_activity.csv", "User-Hotel-Activities"),
        ("./assets/users.csv", "Users"),
    ]
    graphrag: GraphRAG = GraphRAG(path=Path() / "assets" / "graphrag_travel_profile", force=True, auto_delete=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def initialize(self):
        await super().initialize()
        self.agent = AgentExecutor(
            agent=create_tool_calling_agent(
                llm=self.model,
                tools=TravelSQLToolkit(db=ReadOnlySQLDatabase(self.assets), llm=self.model).get_tools(),
                # verbose=True,
                prompt=self.get_chat_prompt_template(additional_messages=[MessagesPlaceholder("agent_scratchpad")]),
            ),
            tools=TravelSQLToolkit(db=ReadOnlySQLDatabase(self.assets), llm=self.model).get_tools(),
        )

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / self.profile.prompts.get_selected_prompt("system").filename,
            template_format="jinja2",
            encoding="utf-8",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / self.profile.prompts.get_selected_prompt("user").filename,
            template_format="jinja2",
            encoding="utf-8",
        ).format(**kwargs)

    @classmethod
    async def load_agent(cls) -> None:
        ...