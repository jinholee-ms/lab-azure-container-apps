import httpx

from langchain_core.tools import tool

from common import settings


@tool(
    "get_current_weather",
    description="Get current weather for a given city.",
)
async def get_current_weather(city: str, units: str = "metric") -> dict:
    """
    Get current weather for a given city.

    Args:
        city (str): City name (e.g., "Seoul")
        units (str): metric, imperial, or standard
    """
    async with httpx.AsyncClient(timeout=10) as client:
        params = {
            "q": city,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": units,
        }
        r = await client.get(f"{settings.OPENWEATHER_ENDPOINT}/data/2.5/weather", params=params)
        r.raise_for_status()
        return r.json()


@tool(
    "get_forecast",
    description="Get 5-day / 3-hour interval forecast for a given city.",
)
async def get_forecast(city: str, units: str = "metric") -> dict:
    """
    Get 5-day / 3-hour interval forecast for a given city.

    Args:
        city (str): City name
        units (str): metric, imperial, standard
    """
    async with httpx.AsyncClient(timeout=10) as client:
        params = {
            "q": city,
            "appid": settings.OPENWEATHER_API_KEY,
            "units": units,
        }
        r = await client.get(f"{settings.OPENWEATHER_ENDPOINT}/data/2.5/forecast", params=params)
        r.raise_for_status()
        return r.json()