from .base import agent_manager
from .orchestrator import Orchestrator
from .planning import PlanningAgent
from .summary import SummaryAgent
from .travel import TravelAgent
from .travel_profile import TravelProfileAgent
from .weather import WeatherAgent
from .web_search import WebSearchAgent


__all__ = [agent_manager, Orchestrator]


async def init_agent_module():
    await agent_manager.initialize_agents()