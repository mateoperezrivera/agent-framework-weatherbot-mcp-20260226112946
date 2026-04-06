import sys
from pathlib import Path

import requests
from agent_framework import MCPStdioTool, tool
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv()


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
    # MCP tool: runs mcp_server.py as a subprocess
    weather_mcp = MCPStdioTool(
        name="weather",
        command=sys.executable,
        args=[str(Path(__file__).with_name("mcp_server.py"))],
        description="Weather MCP server (Open-Meteo, no API key needed)",
    )

    return AzureOpenAIChatClient(
        credential=AzureCliCredential(),
    ).as_agent(
        name="WeatherBot",
        # ✏️ Change the instructions to customize your agent's behavior
        instructions=(
            "You are a friendly assistant. "
            "Use the weather tool for weather questions. "
            "Use get_random_fact when the user asks for trivia. "
            "Keep answers short."
        ),
        # ✏️ Add or remove tools here
        tools=[weather_mcp, get_random_fact],
    )