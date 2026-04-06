"""CLI chat — run with: python cli.py"""

import asyncio
import json
import sys

from agent import create_agent

# ANSI helpers
DIM, CYAN, GREEN, YELLOW, RED, BOLD, RESET = (
    "\033[2m", "\033[36m", "\033[32m", "\033[33m", "\033[31m", "\033[1m", "\033[0m",
)


def _truncate(text, n=400):
    s = str(text)
    return s if len(s) <= n else s[:n] + "..."


def _fmt_args(args):
    if not args:
        return ""
    if isinstance(args, dict):
        return json.dumps(args, ensure_ascii=False)
    try:
        return json.dumps(json.loads(str(args)), ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return str(args)


async def _process_stream(stream):
    printed_text = False
    pending = {}

    async for update in stream:
        for c in update.contents:
            t = c.type

            if t == "text" and c.text:
                if not printed_text:
                    print(BOLD, end="", flush=True)
                    printed_text = True
                print(c.text, end="", flush=True)

            elif t in ("function_call", "mcp_server_tool_call"):
                name = c.name if t == "function_call" else f"{c.server_name}/{c.tool_name}"
                cid = c.call_id or name
                if cid not in pending:
                    pending[cid] = {"name": name, "args": []}
                    label = "tool" if t == "function_call" else "mcp"
                    print(f"\n  {DIM}{CYAN}[{label}]{RESET} calling {BOLD}{name}{RESET}{DIM}...{RESET}", flush=True)
                if c.arguments:
                    pending[cid]["args"].append(str(c.arguments))

            elif t in ("function_result", "mcp_server_tool_result"):
                cid = c.call_id or (c.name if t == "function_result" else f"{c.server_name}/{c.tool_name}")
                info = pending.pop(cid, None)
                if info:
                    args_str = _fmt_args("".join(info["args"])) if info["args"] else ""
                    label = "tool" if t == "function_result" else "mcp"
                    print(f"  {DIM}{CYAN}[{label}]{RESET} {BOLD}{info['name']}{RESET}{DIM}({args_str}){RESET}", flush=True)
                result = _truncate(c.result if t == "function_result" else c.output)
                print(f"  {DIM}{GREEN}[result]{RESET} {DIM}{result}{RESET}", flush=True)

            elif t == "error":
                print(f"\n  {RED}[error]{RESET} {c.message}", flush=True)

    if printed_text:
        print(RESET, end="", flush=True)


async def main():
    print(f"{BOLD}Creating agent...{RESET}")
    agent = create_agent()
    session = agent.create_session()
    print(f"Ready! Type a message (or {DIM}'quit'{RESET} to exit).\n")

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

        print(f"{GREEN}Bot>{RESET} ", end="", flush=True)
        await _process_stream(agent.run(user_input, stream=True, session=session))
        print("\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
