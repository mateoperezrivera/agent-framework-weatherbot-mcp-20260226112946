from __future__ import annotations

from typing import Any

import requests
from mcp import types
from mcp.server import FastMCP
from mcp.server.fastmcp import Context

mcp = FastMCP("local-weather")

_WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
}


def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city using Open-Meteo public APIs (no API key)."""
    geo = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": city, "count": 1, "language": "en", "format": "json"},
    )
    results = geo.get("results") or []
    if not results:
        return f"Could not find city: {city}."

    place = results[0]
    lat = place["latitude"]
    lon = place["longitude"]

    forecast = _get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
    )
    current = forecast.get("current", {})

    temperature = current.get("temperature_2m", "?")
    weather_code = current.get("weather_code")
    wind = current.get("wind_speed_10m", "?")
    condition = _WEATHER_CODES.get(weather_code, f"code {weather_code}")

    city_name = place.get("name", city)
    country = place.get("country", "")
    location = f"{city_name}, {country}" if country else city_name

    return f"{location}: {condition}, {temperature}°C, wind {wind} km/h."


@mcp.tool()
async def generate_greeting(name: str, ctx: Context) -> str:
    """Generate a friendly one-line greeting for a person by asking the host LLM (MCP sampling)."""
    result = await ctx.session.create_message(
        messages=[
            types.SamplingMessage(
                role="user",
                content=types.TextContent(
                    type="text",
                    text=f"Write a short, friendly one-line greeting for {name}. Reply with the greeting only.",
                ),
            )
        ],
        max_tokens=100,
    )
    if isinstance(result.content, types.TextContent):
        return result.content.text
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="stdio")
