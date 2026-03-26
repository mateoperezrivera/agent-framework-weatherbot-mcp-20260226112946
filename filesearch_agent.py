"""Agent that uses Azure OpenAI Responses API with file search over a vector store.

Reads all files from a local `files/` folder, uploads them to Azure OpenAI,
creates a vector store, and configures the agent with the file_search tool.

Usage:
    1. Put your documents in a `files/` folder next to this script.
    2. Set env vars (AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME).
    3. Run: python filesearch_agent.py
"""

import os
import sys
from pathlib import Path

from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.observability import enable_instrumentation, create_resource
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor(
        resource=create_resource(),
        enable_live_metrics=True,
    )
    enable_instrumentation()

FILES_DIR = Path(__file__).with_name("files")


def get_openai_client() -> AzureOpenAI:
    """Create a raw AzureOpenAI client for file/vector store management."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    kwargs = {
        "api_version": "2025-03-01-preview",
        "azure_endpoint": endpoint,
    }
    if api_key:
        kwargs["api_key"] = api_key
    else:
        from azure.identity import get_bearer_token_provider
        credential = AzureCliCredential()
        kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
            credential, "https://cognitiveservices.azure.com/.default"
        )

    return AzureOpenAI(**kwargs)


def upload_files_and_create_vector_store(client: AzureOpenAI) -> str:
    """Upload all files in FILES_DIR and create a vector store. Returns the vector store ID."""
    if not FILES_DIR.exists() or not any(FILES_DIR.iterdir()):
        print(f"No files found in {FILES_DIR}. Create a 'files/' folder with documents.")
        sys.exit(1)

    file_ids = []
    for file_path in sorted(FILES_DIR.iterdir()):
        if file_path.is_file():
            print(f"  Uploading {file_path.name}...", end=" ", flush=True)
            with open(file_path, "rb") as f:
                uploaded = client.files.create(file=f, purpose="assistants")
            file_ids.append(uploaded.id)
            print(f"OK ({uploaded.id})")

    if not file_ids:
        print("No files were uploaded.")
        sys.exit(1)

    print(f"Creating vector store with {len(file_ids)} file(s)...", end=" ", flush=True)
    vector_store = client.vector_stores.create(
        name="filesearch-agent-store",
        file_ids=file_ids,
    )
    print(f"OK ({vector_store.id})")

    return vector_store.id


def create_agent():
    print("Setting up file search agent...")

    openai_client = get_openai_client()
    vector_store_id = upload_files_and_create_vector_store(openai_client)

    responses_client = AzureOpenAIResponsesClient(
        credential=AzureCliCredential(),
    )

    file_search_tool = responses_client.get_file_search_tool(
        vector_store_ids=[vector_store_id],
    )

    return responses_client.as_agent(
        name="FileSearchAgent",
        instructions=(
            "You are a helpful assistant that answers questions based on the uploaded documents. "
            "Use the file_search tool to find relevant information in the documents. "
            "Always cite which document your answer comes from. "
            "If the answer is not in the documents, say so."
        ),
        tools=[file_search_tool],
    )
