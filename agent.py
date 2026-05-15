import os
import sys
from pathlib import Path

import requests
from agent_framework import MCPStdioTool, MCPStreamableHTTPTool, tool
from agent_framework.openai import OpenAIChatClient
from dotenv import load_dotenv

load_dotenv()

# Optional: App Insights tracing (set APPLICATIONINSIGHTS_CONNECTION_STRING in .env)
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from agent_framework.observability import enable_instrumentation, create_resource
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(resource=create_resource(), enable_live_metrics=True)
    enable_instrumentation()


# --- Inline tools (use the @tool decorator) ---

@tool
def get_random_fact() -> str:
    """Get a random cat fact from a public API."""
    try:
        resp = requests.get("https://catfact.ninja/fact", timeout=10)
        resp.raise_for_status()
        return resp.json().get("fact", "No fact available.")
    except Exception as ex:
        return f"Could not fetch fact: {ex}"


# --- Agent definition ---

def create_agent():
    # Shared chat client. Also passed to the MCP tool so the server can use
    # MCP "sampling" to ask the host LLM for completions.
    chat_client = OpenAIChatClient()

    # MCP tool: runs mcp_server.py as a subprocess
    weather_mcp = MCPStdioTool(
        name="weather",
        command=sys.executable,
        args=[str(Path(__file__).with_name("mcp_server.py"))],
        description="Weather MCP server (Open-Meteo, no API key needed)",
        client=chat_client,  # enables MCP sampling callbacks from the server
    )

    # Remote MCP tool: Microsoft Learn documentation
    ms_learn_mcp = MCPStreamableHTTPTool(
        name="ms_learn",
        url="https://learn.microsoft.com/api/mcp",
        description="Microsoft Learn MCP server",
    )

    return chat_client.as_agent(
        name="WeatherBot",
        # ✏️ Change the instructions to customize your agent's behavior
        instructions=(
            "You are a friendly assistant. "
            "Use the weather tool for weather questions. "
            "Use the ms_learn tool for Microsoft Learn documentation questions. "
            "Use get_random_fact when the user asks for trivia. "
            "Keep answers short."
        ),
        # ✏️ Add or remove tools here
        tools=[weather_mcp, ms_learn_mcp, get_random_fact],
    )