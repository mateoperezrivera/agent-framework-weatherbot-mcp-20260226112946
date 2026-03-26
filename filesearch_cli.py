"""CLI chat for the file search agent.

Usage:
    1. Put documents in a `files/` folder next to this script.
    2. Run: python filesearch_cli.py
"""

import asyncio
import json
import sys

from filesearch_agent import create_agent
from agent_framework.observability import get_tracer
from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import format_trace_id

# ANSI colors
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
MAGENTA = "\033[35m"
RESET = "\033[0m"


def truncate(text, max_len=400):
    s = str(text)
    return s if len(s) <= max_len else s[:max_len] + "..."


def format_args(arguments):
    if not arguments:
        return ""
    if isinstance(arguments, dict):
        return json.dumps(arguments, ensure_ascii=False)
    try:
        parsed = json.loads(str(arguments))
        return json.dumps(parsed, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return str(arguments)


def print_citations(annotations):
    """Print file citations from annotations."""
    if not annotations:
        return
    seen = set()
    for ann in annotations:
        if ann.get("type") != "citation":
            continue
        title = ann.get("title", "unknown")
        if title in seen:
            continue
        seen.add(title)
        snippet = ann.get("snippet", "")
        if snippet:
            snippet = truncate(snippet, 150)
            print(f"  {DIM}{MAGENTA}[source]{RESET} {BOLD}{title}{RESET} {DIM}— \"{snippet}\"{RESET}", flush=True)
        else:
            print(f"  {DIM}{MAGENTA}[source]{RESET} {BOLD}{title}{RESET}", flush=True)


async def process_stream(stream):
    printed_text = False
    pending_calls = {}
    all_annotations = []

    async for update in stream:
        for content in update.contents:
            t = content.type

            if t == "text" and content.text:
                if not printed_text:
                    print(f"{BOLD}", end="", flush=True)
                    printed_text = True
                print(content.text, end="", flush=True)
                if content.annotations:
                    all_annotations.extend(content.annotations)

            elif t == "function_call":
                cid = content.call_id or content.name
                if cid not in pending_calls:
                    pending_calls[cid] = {"name": content.name, "args_parts": []}
                    print(f"\n  {DIM}{CYAN}[tool]{RESET} calling {BOLD}{content.name}{RESET}{DIM}...{RESET}", flush=True)
                if content.arguments:
                    pending_calls[cid]["args_parts"].append(str(content.arguments))

            elif t == "function_result":
                cid = content.call_id or content.name
                call_info = pending_calls.pop(cid, None)
                if call_info:
                    full_args = "".join(call_info["args_parts"])
                    args_str = format_args(full_args) if full_args else ""
                    print(f"  {DIM}{CYAN}[tool]{RESET} {BOLD}{call_info['name']}{RESET}{DIM}({args_str}){RESET}", flush=True)
                result_str = truncate(content.result)
                print(f"  {DIM}{GREEN}[result]{RESET} {DIM}{result_str}{RESET}", flush=True)

            elif t == "error":
                print(f"\n  {RED}[error]{RESET} {content.message}", flush=True)

    if printed_text:
        print(RESET, end="", flush=True)

    if all_annotations:
        print(f"\n  {DIM}───────────────{RESET}")
        print_citations(all_annotations)


async def chat_loop():
    with get_tracer().start_as_current_span("FileSearch Agent Chat", kind=SpanKind.CLIENT) as current_span:
        print(f"Trace ID: {format_trace_id(current_span.get_span_context().trace_id)}")
        print(f"{BOLD}Creating file search agent...{RESET}")
        agent = create_agent()
        session = agent.create_session()
        print(f"FileSearch CLI ready. Type your message (or {DIM}'quit'{RESET} to exit).\n")

        while True:
            try:
                user_input = input(f"{YELLOW}You>{RESET} ")
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if user_input.strip().lower() in ("quit", "exit", "q"):
                print("Bye!")
                break

            if not user_input.strip():
                continue

            stream = agent.run(user_input, stream=True, session=session)

            print(f"{GREEN}Bot>{RESET} ", end="", flush=True)
            await process_stream(stream)

            print("\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(chat_loop())
