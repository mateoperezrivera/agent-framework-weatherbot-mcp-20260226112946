import os
import sys
from pathlib import Path

import requests
from agent_framework import MCPStdioTool, MCPStreamableHTTPTool, tool
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import enable_instrumentation,create_resource,get_tracer
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(
        resource=create_resource(),
    enable_live_metrics=True,
    )
    enable_instrumentation()


@tool
def get_random_fact() -> str:
    """Get a random fact from a public API (Cat Facts)."""
    try:
        response = requests.get("https://catfact.ninja/fact", timeout=10)
        response.raise_for_status()
        data = response.json()
        return str(data.get("fact", "No fact available right now."))
    except Exception as ex:
        return f"Could not fetch fact right now: {ex}"


def create_agent():
    local_weather_server = str(Path(__file__).with_name("local_weather_mcp.py"))
    local_weather_mcp = MCPStdioTool(
        name="local_weather",
        command=sys.executable,
        args=[local_weather_server],
        description="Local weather MCP server backed by Open-Meteo public API",
    )

    tools = [local_weather_mcp, get_random_fact]
    if os.getenv("MS_LEARN_MCP_ENABLED", "true").lower() == "true":
        tools.append(
            MCPStreamableHTTPTool(
                name="ms_learn",
                url=os.getenv("MS_LEARN_MCP_URL", "https://learn.microsoft.com/api/mcp"),
                description="Microsoft Learn MCP server",
            )
        )

    return AzureOpenAIChatClient(
        credential=AzureCliCredential(),
    ).as_agent(
        name="WeatherBot",
        instructions=(
            "You are a friendly assistant. "
            "Use the local_weather MCP tool for weather questions and use the ms_learn MCP tools for Microsoft Learn documentation questions. "
            "Use get_random_fact when the user asks for trivia/facts. "
            "Keep answers short."
        ),
        tools=tools,
    )