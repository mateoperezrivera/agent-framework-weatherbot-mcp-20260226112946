# WeatherBot — AI Agent Starter Template

An AI agent that answers weather questions using MCP tools, built with [Azure AI Agent Framework](https://pypi.org/project/agent-framework/).

## Quickstart

### 1. Prerequisites

- Python 3.10+
- Azure CLI (`az login` — used for authentication, no API keys needed)
- An Azure OpenAI model deployed in [Azure AI Foundry](https://ai.azure.com)

### 2. Install

```bash
pip install -r requirements.txt
```

### 3. Configure

Copy `.env.example` to `.env` and fill in your values:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4o
```

### 4. Run

```bash
az login
python main.py        # Opens DevUI at http://127.0.0.1:8070
# or
python cli.py         # Terminal chat interface
```

---

## Project Structure

| File | Purpose |
|---|---|
| `agent.py` | Agent definition — **edit this** to change behavior |
| `mcp_server.py` | MCP tools — **edit this** to add your own tools |
| `main.py` | DevUI entry point — **primary way to test** |
| `cli.py` | CLI chat (alternative) |

---

## Adding Your Own Tools

### Option 1: `@tool` decorator (inline in `agent.py`)

Add a function with the `@tool` decorator directly in `agent.py`:

```python
from agent_framework import tool

@tool
def my_tool(query: str) -> str:
    """Description of what this tool does."""
    return "result"
```

Then add it to the tools list in `create_agent()`.

### Option 2: `@mcp.tool()` in the MCP server (`mcp_server.py`)

Add a function in `mcp_server.py`:

```python
@mcp.tool()
def my_tool(param: str) -> str:
    """Description of what this tool does."""
    return "result"
```

MCP tools are automatically available to the agent — no changes needed in `agent.py`.

> **When to use which?** Use `@tool` for simple, self-contained functions. Use `@mcp.tool()` when the tool needs its own dependencies or you want to run it as a separate server.

---

## Getting Your Environment Variables

1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Open (or create) a **project**
3. Go to **Deployments** in the left menu
4. If no model is deployed, click **+ Deploy model** → choose a model (e.g. `gpt-4o`) → Deploy
5. Click on your deployment to see:
   - **Endpoint** → use as `AZURE_OPENAI_ENDPOINT`
   - **Deployment name** → use as `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`

### Deploying a Model

If you need to deploy a model:

1. In your AI Foundry project, go to **Model catalog**
2. Search for the model you want (e.g. `gpt-4o`, `gpt-4o-mini`)
3. Click **Deploy** → choose a deployment name → confirm
4. Copy the endpoint and deployment name into your `.env`

---

## Customizing the Agent

In `agent.py`, you can change:

- **`instructions`** — the system prompt that defines the agent's personality and behavior
- **`name`** — the agent's name
- **`tools`** — the list of tools available to the agent
