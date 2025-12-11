from .base import agent_manager
from .chatbot import ChatbotAgent
from .planning import PlanningAgent
from .travel import TravelAgent
from .travel_itinerary_suggestion import TravelItinerarySuggestionAgent
from .travel_profile import TravelProfileAgent
from .travel_recommend import TravelRecommendAgent
from .travel_summary import TravelSummaryAgent
from .triage import TriageAgent
from .weather import WeatherAgent
from .web_search import WebSearchAgent


__all__ = [agent_manager]


async def load_agents() -> None:
    await TravelProfileAgent.load_agent()