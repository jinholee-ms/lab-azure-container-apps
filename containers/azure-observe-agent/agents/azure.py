import os
from pydantic import BaseModel, Field
from queue import Queue
from typing import Any, Dict, List, Optional
from textwrap import dedent

from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.resource.subscriptions import SubscriptionClient

from langchain_openai import AzureChatOpenAI
from langchain.tools import StructuredTool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.callbacks.base import BaseCallbackHandler


class SubmitSubTaskPlanInput(BaseModel):
    name: str = Field(..., description="subtask 이름")
    description: str = Field(..., description="subtask 설명")


class SubmitTaskPlanInput(BaseModel):
    name: str = Field(..., description="이번 task 이름")
    description: str = Field(..., description="이번 task 설명")
    total_subtasks: int = Field(..., description="예상 총 subtask 수")
    subtasks: List[SubmitSubTaskPlanInput] = Field(..., description='이번 작업에 포함된 subtask 목록')
    

class SubmitSubtaskUpdateInput(BaseModel):
    name: str = Field(..., description="현재 진행 중인 subtask 이름")
    status: str = Field(..., description="현재 진행 중인 subtask 상태, 예: ready, in_progress, completed, failed")


class SubmitTaskUpdateInput(BaseModel):
    name: str = Field(..., description="현재 진행 중인 task 이름")
    status: str = Field(..., description="현재 진행 중인 task 상태, 예: ready, in_progress, completed, failed")
    updated_subtasks: List[SubmitSubtaskUpdateInput] = Field(..., description='이번 작업에 포함된 subtask 목록')


class ListRGInput(BaseModel):
    subscription_ids: Optional[List[str]] = Field(
        default=None, description="대상 구독 ID 목록. 비워두면 접근 가능한 모든 구독에서 조회합니다."
    )
    name_contains: Optional[str] = Field(
        default=None, description="리소스 그룹 이름 부분일치 필터(소문자 비교)."
    )
    limit: Optional[int] = Field(
        default=None, description="최대 반환 개수(클라이언트 슬라이스)."
    )
    
    
class ListResourcesInRGInput(BaseModel):
    subscription_id: str = Field(..., description="대상 구독 ID")
    resource_group: str = Field(..., description="리소스 그룹 이름")
    name_contains: Optional[str] = Field(default=None, description="리소스 이름 부분일치")
    type_contains: Optional[str] = Field(default=None, description="리소스 타입 부분일치")
    limit: Optional[int] = Field(default=None, description="최대 반환 개수")


class AzureInventoryAgentCallabackHandler(BaseCallbackHandler):
    def __init__(self, queue: Queue):
        super().__init__()
        self._queue = queue

    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        self._queue.put({
            "type": "log",
            "level": "info",
            "message": {
                "type": "tool_start",
                "input": input_str,
            },
        })
        
    def on_tool_end(self, output, *, run_id, parent_run_id = None, **kwargs):
        self._queue.put({
            "type": "log",
            "level": "info",
            "message": {
                "type": "tool_end",
                "output": output,
            },
        })
    

class AzureToolCollection:
    def __init__(self, queue: Queue):
        self._queue = queue

    @property
    def tools(self) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self.submit_task_plan,
                name="submit_task_plan",
                description="수행 전에 이번 Task 계획을 제출합니다.",
                args_schema=SubmitTaskPlanInput,
            ),
            StructuredTool.from_function(
                func=self.submit_task_update,
                name="submit_task_update",
                description="Task 수행 중 업데이트 내용을 제출합니다.",
                args_schema=SubmitTaskUpdateInput,
            ),
            StructuredTool.from_function(
                func=self.list_resources_in_resource_group,
                name="list_resources_in_resource_group",
                description="특정 리소스 그룹 내부의 리소스를 나열합니다.",
                args_schema=ListResourcesInRGInput,
            ),
            StructuredTool.from_function(
                func=self.list_resource_groups,
                name="list_resource_groups",
                description="여러 구독에 걸쳐 접근 가능한 모든 리소스 그룹을 나열합니다.",
                args_schema=ListRGInput,
            ),
        ]

    def submit_task_plan(
        self,
        name: str,
        description: str,
        total_subtasks: int,
        subtasks: List[SubmitSubTaskPlanInput],
    ) -> str:
        self._queue.put(
            {
                "type": "task_plan",
                "message": SubmitTaskPlanInput(
                    name=name,
                    description=description,
                    total_subtasks=total_subtasks,
                    subtasks=subtasks,
                )
            },
        )
        return "Task plan submitted successfully."

    def submit_task_update(
        self,
        name: str,
        status: str,
        updated_subtasks: List[SubmitSubtaskUpdateInput],
    ) -> str:
        self._queue.put(
            {
                "type": "task_update",
                "message": SubmitSubtaskUpdateInput(
                    name=name,
                    status=status,
                    updated_subtasks=updated_subtasks,
                ),
            }
        )
        return "Task update submitted successfully."

    def list_resource_groups(
        self,
        subscription_ids: Optional[List[str]] = None,
        name_contains: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not subscription_ids:
            sub_client = SubscriptionClient(DefaultAzureCredential())
            subscription_ids = [s.subscription_id for s in sub_client.subscriptions.list()]
        for sub_id in subscription_ids:
            rm = ResourceManagementClient(DefaultAzureCredential(), sub_id)
            for rg in rm.resource_groups.list():
                item = {
                    "id": rg.id,
                    "name": rg.name,
                    "location": getattr(rg, "location", None),
                    "subscriptionId": sub_id,
                    "tags": getattr(rg, "tags", None),
                }
                if name_contains and name_contains.lower() not in (rg.name or "").lower():
                    continue
                out.append(item)
                if limit and len(out) >= limit:
                    return out
        return out
    
    def list_resources_in_resource_group(
        self,
        subscription_id: str,
        resource_group: str,
        name_contains: Optional[str] = None,
        type_contains: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        rm = ResourceManagementClient(DefaultAzureCredential(), subscription_id)
        out: List[Dict[str, Any]] = []
        pager = rm.resources.list_by_resource_group(resource_group)
        for res in pager:
            item = {
                "id": getattr(res, "id", None),
                "name": getattr(res, "name", None),
                "type": getattr(res, "type", None),
                "location": getattr(res, "location", None),
                "resourceGroup": resource_group,
                "subscriptionId": subscription_id,
                "tags": getattr(res, "tags", None),
            }
            if name_contains and name_contains.lower() not in (item["name"] or "").lower():
                continue
            if type_contains and type_contains.lower() not in (item["type"] or "").lower():
                continue
            out.append(item)
            if limit and len(out) >= limit:
                return out
        return out
    

class AzureInventoryAgent:
    name: str = "Azure Inventory Agent"
    description: str = "An agent that can answer questions about Azure resources."
    
    def __init__(
        self,
        queue: Queue,
    ):
        self._queue = queue
        self._tool_collection = AzureToolCollection(queue)
        self._executor = AgentExecutor(
            agent=create_tool_calling_agent(
                llm=AzureChatOpenAI(
                    azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
                    model=os.environ["AZURE_OPENAI_MODEL"],
                    temperature=0,
                    streaming=False,
                ),
                tools=self._tool_collection.tools,
                prompt=AzureInventoryAgent.create_prompt_template(),
            ),
            tools=self._tool_collection.tools,
            verbose=True,
            max_iterations=120,
            handle_parsing_errors=True,
            callbacks=[AzureInventoryAgentCallabackHandler(queue)],
        )
    
    def entrypoint(self, input: str):
        try:
            response = self._executor.invoke(
                {
                    "input": input,
                    "chat_history": [],
                },
                # config={"callback": [self._handler]},
            )
        except Exception as e:
            print(f"Error during agent execution: {e}")
            response = {"error": str(e)}

        self._queue.put({
            "type": "response",
            "data": response,
        })

    @staticmethod
    def create_prompt_template() -> ChatPromptTemplate:
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system", dedent("""
                    너는 Azure Inventory Agent 야. 
                    사용자의 요구를 달성하기 위해 아래 도구들을 자율적으로 Task 를 계획/호출하여 수행할 수 있어.
                    결과가 많더라도 빠짐없이 모두 조사해서 알려줘. 
                    구독 스코프는 리소스는 누락될 수 있지만, 기본적으로 Subscription ID=f3d1de09-72d9-4869-90b2-3daf03eecda2 을 기준으로 해.
                    
                    Task 수행 과정에서 다음을 따라줘.
                    - 수행 전에 반드시 `submit_task_plan` 도구를 사용해 이번 작업 계획을 제출해야 해.
                    - Task 수행 중 업데이트 내용은 `submit_task_update` 도구를 사용해 제출할 수 있어.
                    """),
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder("agent_scratchpad"),
            ],
        )
