from agent_framework_devui import serve

from agent import create_agent


def main() -> None:
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
