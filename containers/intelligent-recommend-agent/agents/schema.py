import datetime
from typing import Any, Optional, TypedDict
from uuid import uuid4

from pydantic import BaseModel, Field


class PlanningStepArgument(BaseModel):
    title: str = Field(description="Short title of the step")
    description: str = Field(description="What to do in this step")
    agent: str = Field(description="Agent responsible for this step")
    question: str = Field(description="Question or input for this step")
    use_answers_from: list[int] = Field(
        default_factory=list,
        description=(
            "Indices of previous steps whose answers should be provided "
            "as context when executing this step. "
            "Indices are 0-based and must refer only to earlier steps."
        ),
    )


class PlanningStepsArgument(BaseModel):
    steps: list[PlanningStepArgument]


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


class AgentGraphInput(BaseModel):
    question: str
    agents: list


class AgentGraphState(BaseModel):
    session_id: str
    input: AgentGraphInput
    workflow: Workflow = None
    answer: str = None
