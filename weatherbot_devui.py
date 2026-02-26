import os
import sys
from pathlib import Path
from agent_framework import MCPStdioTool, MCPStreamableHTTPTool
import requests
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_devui import serve
from azure.identity import AzureCliCredential
from dotenv import load_dotenv


from agent_framework import tool
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

    return AzureOpenAIResponsesClient(
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


def load_environment() -> None:
    # Load .env from current working dir and script dir (if present)
    load_dotenv()
    script_env = Path(__file__).with_name(".env")
    if script_env.exists():
        load_dotenv(script_env)

    # Support common alias variable names
    aliases = {
        "AZURE_FOUNDRY_PROJECT_ENDPOINT": ["AZURE_AI_PROJECT_ENDPOINT"],
        "AZURE_FOUNDRY_PROJECT_DEPLOYMENT_NAME": ["AZURE_AI_MODEL_DEPLOYMENT_NAME"],
        "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME": [
            "AZURE_FOUNDRY_PROJECT_DEPLOYMENT_NAME",
            "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
            "AZURE_OPENAI_DEPLOYMENT_NAME",
        ],
    }
    for target, candidates in aliases.items():
        if os.getenv(target):
            continue
        for source in candidates:
            value = os.getenv(source)
            if value:
                os.environ[target] = value
                break



def main() -> None:
    load_environment()
    print("Weather MCP server: local_weather_mcp.py (Open-Meteo, no API key)")
    agent = create_agent()

    print("Starting DevUI at http://127.0.0.1:8070")
    serve(
        entities=[agent],
        port=8070,
        auto_open=True,
        instrumentation_enabled=True,
    )


if __name__ == "__main__":
    main()
