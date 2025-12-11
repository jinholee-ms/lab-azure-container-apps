import datetime
from typing import Any, Optional, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentProfile(BaseModel):
    name: str = Field(description="Name of the agent")
    description: str = Field(description="Description of the agent's purpose and capabilities")
    task_operator: Any = Field(description="Task operator class associated with the agent")
    chat_in_settings: bool = Field(default=True, description="Whether to chat to this agent in chat settings")


class PlanningStepArgument(BaseModel):
    title: str = Field(description="Short title of the step")
    description: str = Field(description="What to do in this step")
    agent: str = Field(description="Agent responsible for this step")
    question: str = Field(description="Question or input for this step")


class PlanningStepsArgument(BaseModel):
    steps: list[PlanningStepArgument] = Field(description="List of planning steps")


class TriageAgentOutput(BaseModel):
    action: str = Field(description="The action to take, e.g., 'route' or 'clarify'")
    agent: Optional[str] = Field(description="Agent selected for 'route' action")
    reason: Optional[str] = Field(description="Reason for the 'route' action")
    question: Optional[str] = Field(description="Clarification question for 'clarify' action")


class Task(PlanningStepArgument):
    id: int = Field(default_factory=lambda: uuid4().int)
    started_at: Optional[datetime.datetime] = None
    finished_at: Optional[datetime.datetime] = None
    answer: Optional[str] = None


class Workflow(BaseModel):
    tasks: list[Task] = Field(default_factory=list)

    def get_next_task(self) -> Optional[Task]:
        for task in self.tasks:
            if task.finished_at is None:
                return task
        return None

    def get_last_task(self) -> Optional[Task]:
        if self.tasks:
            return self.tasks[-1]
        return None


class AgentContextBase(BaseModel):
    ...


class TriageAgentContext(AgentContextBase):
    selected_agent_name: Optional[str] = None


class TravelAgentContext(AgentContextBase):
    profile: Optional[str] = None
    searched_data: Optional[str] = None
    itinerary_suggestion: Optional[str] = None
    recommendations: Optional[str] = None


class AgentGraphStateBase(BaseModel):
    question: str
    answer: Optional[str] = None
    context: Optional[Any] = None


class PlannedAgentGraphState(AgentGraphStateBase):
    sub_agents: list[Any] = []
    workflow: Optional[Workflow] = None