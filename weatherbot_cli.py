"""CLI chat interface for WeatherBot agent.

Usage:
    python weatherbot_cli.py

Provides a REPL where you can chat with the agent and see tool calls/results streamed in real time.
"""

import asyncio
import json
import sys

from agent import create_agent
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


def print_tool_call(name, arguments, prefix="tool"):
    args_str = format_args(arguments)
    print(f"\n  {DIM}{CYAN}[{prefix}]{RESET} {BOLD}{name}{RESET}{DIM}({args_str}){RESET}", flush=True)


def print_tool_result(name, result, prefix="tool"):
    result_str = truncate(result)
    print(f"  {DIM}{GREEN}[{prefix} result]{RESET} {name} {DIM}-> {result_str}{RESET}", flush=True)


def print_error(message):
    print(f"\n  {RED}[error]{RESET} {message}", flush=True)


async def process_stream(stream):
    """Process a response stream, buffering tool calls and streaming text."""
    printed_text = False
    # Buffer tool calls: streamed chunks have fragmented arguments,
    # so we accumulate them and print once the result arrives.
    pending_calls = {}  # call_id -> {name, args_parts}

    async for update in stream:
        for content in update.contents:
            t = content.type

            if t == "text" and content.text:
                if not printed_text:
                    print(f"{BOLD}", end="", flush=True)
                    printed_text = True
                print(content.text, end="", flush=True)

            elif t == "function_call":
                cid = content.call_id or content.name
                if cid not in pending_calls:
                    pending_calls[cid] = {"name": content.name, "args_parts": []}
                    print(f"\n  {DIM}{CYAN}[tool]{RESET} calling {BOLD}{content.name}{RESET}{DIM}...{RESET}", flush=True)
                args_chunk = content.arguments
                if args_chunk:
                    pending_calls[cid]["args_parts"].append(str(args_chunk))

            elif t == "function_result":
                cid = content.call_id or content.name
                call_info = pending_calls.pop(cid, None)
                if call_info:
                    full_args = "".join(call_info["args_parts"])
                    args_str = format_args(full_args) if full_args else ""
                    print(f"  {DIM}{CYAN}[tool]{RESET} {BOLD}{call_info['name']}{RESET}{DIM}({args_str}){RESET}", flush=True)
                result_str = truncate(content.result)
                print(f"  {DIM}{GREEN}[result]{RESET} {DIM}{result_str}{RESET}", flush=True)

            elif t == "mcp_server_tool_call":
                label = f"{content.server_name}/{content.tool_name}"
                cid = content.call_id or label
                if cid not in pending_calls:
                    pending_calls[cid] = {"name": label, "args_parts": []}
                    print(f"\n  {DIM}{CYAN}[mcp]{RESET} calling {BOLD}{label}{RESET}{DIM}...{RESET}", flush=True)
                args_chunk = content.arguments
                if args_chunk:
                    pending_calls[cid]["args_parts"].append(str(args_chunk))

            elif t == "mcp_server_tool_result":
                label = f"{content.server_name}/{content.tool_name}"
                cid = content.call_id or label
                call_info = pending_calls.pop(cid, None)
                if call_info:
                    full_args = "".join(call_info["args_parts"])
                    args_str = format_args(full_args) if full_args else ""
                    print(f"  {DIM}{CYAN}[mcp]{RESET} {BOLD}{call_info['name']}{RESET}{DIM}({args_str}){RESET}", flush=True)
                result_str = truncate(content.output)
                print(f"  {DIM}{GREEN}[result]{RESET} {DIM}{result_str}{RESET}", flush=True)

            elif t == "error":
                print_error(content.message)

    if printed_text:
        print(RESET, end="", flush=True)


async def chat_loop():
    with get_tracer().start_as_current_span("Weather Agent Chat", kind=SpanKind.CLIENT) as current_span:
        print(f"Trace ID: {format_trace_id(current_span.get_span_context().trace_id)}")
        print(f"{BOLD}Creating agent...{RESET}")
        agent = create_agent()
        session = agent.create_session()
        print(f"WeatherBot CLI ready. Type your message (or {DIM}'quit'{RESET} to exit).\n")

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
