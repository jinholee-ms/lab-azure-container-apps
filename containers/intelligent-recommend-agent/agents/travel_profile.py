from textwrap import dedent
from datetime import datetime
from uuid import uuid4
import os
from pathlib import Path
import subprocess
from typing import Any
import pandas as pd

from langchain_community.agent_toolkits.sql.base import create_sql_agent, SQLDatabaseToolkit
from langchain.prompts import PromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.tools import tool

from agents.base import AgentBase, TaskOperator
from agents.schema import AgentGraphState, Task
from capabilities.db import ReadOnlySQLDatabase
from capabilities.graphrag import GraphRAG
from common import console


@tool(
    "get_travel_profile_from_graphrag",
    description=dedent(
    """
    사용자의 여행 활동, 호텔 방문 기록, 선호도, 리뷰 히스토리를 기반으로 개인화된 여행 프로필을 구성하는데 필요한 정보를 Graphrag에서 검색합니다。
    """
    ),
)
async def get_travel_profile_from_graphrag(question: str) -> str:
    return await TravelProfileAgent.graphrag.retrieve_on_global(question)


class TravelProfileOperator(TaskOperator):
    async def exec(
        self,
        state: AgentGraphState,
        task: Task = None,
        previous_tasks: list[Task] = None,
    ) -> None:
        response = await self.agent.run_langchain_agent(
            self.agent.generate_system_prompt(),
            self.agent.generate_user_prompt(question=task.question),
            session_id=state.session_id,
        )

        task.answer = self.agent.extract_langchain_agent_answer(response)


class TravelSQLToolkit(SQLDatabaseToolkit):
    def get_tools(self):
        # 원래 SQL용 도구들
        tools = super().get_tools()
        # 여기에 Graphrag tool 추가
        tools.append(get_travel_profile_from_graphrag)
        return tools


class TravelProfileAgent(AgentBase):
    name: str = "TravelProfileAgent"
    description: str = (
        "사용자의 여행 활동, 호텔 방문 기록, 선호도, 리뷰 히스토리를 기반으로 개인화된 여행 프로필을 구성하고, "
        "다른 에이전트 사용할 수 있는 관련 정보 (추천 호텔, 선호 지역, 여행 패턴 등) 을 제공하는 에이전트"
    )
    activated: bool = True
    locked: bool = False
    task_operator = TravelProfileOperator

    graphrag: GraphRAG = GraphRAG(force=True, auto_delete=True)
    # graphrag: GraphRAG = GraphRAG(force=True, auto_delete=False)
    _sql_chain = None # _sql_agent 대신 _sql_chain 사용

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: ReadOnlySQLDatabase = None

    async def initialize(self):
        # Load CSV files into in-memory SQLite database
        assets = [
            ("./assets/hotels.csv", "Hotels"),
            ("./assets/user_hotel_activity.csv", "User-Hotel-Activities"),
            ("./assets/users.csv", "Users"),
        ]

        # Check if any asset files are missing
        if any(not os.path.exists(filename) for filename, _ in assets):
            console.print("⏱️ Asset files are missing. Running gen_travel_db_kr.py...")
            result = subprocess.run(
                ["python", "gen_travel_db_kr.py"], cwd="./assets",check=True, capture_output=True, text=True,
            )
            if result.stderr:
                console.print(f"❌ {result.stderr}")
            else:
                console.print("✅ Asset files generated successfully.")

        self.db = ReadOnlySQLDatabase(assets)

        # Load documents for GraphRAG
        graphrag_input_dir = "./assets/graphrag_input"
        if not os.path.isdir(graphrag_input_dir) or not os.listdir(graphrag_input_dir):
            console.print("⏱️ GraphRAG input files are missing. Running gen_travel_graphrag_input.py...")
            result = subprocess.run(
                ["python", "gen_travel_graphrag_input.py"], cwd="./assets",check=True, capture_output=True, text=True,
            )
            if result.stderr:
                console.print(f"❌ {result.stderr}")
            else:
                console.print("✅ GraphRAG input files generated successfully.")

        # Read all .txt files from graphrag_input directory
        documents = []
        for txt_file in Path(graphrag_input_dir).glob("*.txt"):
            with open(txt_file, "r", encoding="utf-8") as f:
                raw = f.read()
                first_line = raw.splitlines()[0].lstrip("# ").strip()

                documents.append({"title": first_line, "text": raw, "id": txt_file.name, "creation_date": datetime.now().isoformat()})
        # Convert to DataFrame
        documents = pd.DataFrame(documents)

        await self.graphrag.build(documents=documents)

    def generate_system_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_profile_system_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    def generate_user_prompt(self, **kwargs) -> str:
        return PromptTemplate.from_file(
            Path(__file__).parent / "prompts" / "travel_profile_human_prompt.jinja",
            template_format="jinja2",
        ).format(**kwargs)

    async def get_tools(self) -> list[callable]:
        return [get_travel_profile_from_graphrag]

    async def get_sql_agent(self, system_prompt: str):
        if self._sql_chain is not None:
            return self._sql_chain

        llm = await self.get_model(include_tools=False)

        # 1) SQLDatabaseChain 생성
        toolkit = TravelSQLToolkit(db=self.db, llm=llm)

        # 2. create_sql_agent를 사용하여 Agent Executor 생성
        sql_agent_executor = create_sql_agent(
            llm=llm,
            toolkit=toolkit, # SQLDatabase 객체가 아닌 toolkit을 전달
            # verbose=True,
            # 0.x 버전의 create_sql_agent는 'use_query_checker' 인자를 직접 받지 않을 수 있습니다.
            # (버전 따라 다름. 여기서는 생략)
        )

        self._sql_agent = sql_agent_executor
        # 0.x에서는 RunnableWithMessageHistory를 사용하기 어려우므로 Agent Executor 자체를 반환합니다.
        return self._sql_agent

    async def run_langchain_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        session_id: str = uuid4().hex,
        response_format: Any = None,
    ) -> Any:
        """
        0.x 버전의 SQLDatabaseChain을 사용하여 실행합니다.
        """
        sql_chain = await self.get_sql_agent(system_prompt=system_prompt)

        full_input = f"{system_prompt}\n\n{user_prompt}"
        # 0.x SQLDatabaseChain의 입력은 'query' 또는 'input'입니다.
        response = await sql_chain.ainvoke(
            {"input": full_input}
        )

        return response