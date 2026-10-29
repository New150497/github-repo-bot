"""
repo_bot.py - GitHub repo automation using OmniRoute local gateway.
Windows Native + Shallow Clone + Auto Rate-Limit / Cooldown Handler.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from openai import OpenAI

# লোকাল ডিরেক্টরি পাথ
WORKSPACE = Path(
    os.environ.get("REPO_WORKSPACE", str(Path(__file__).resolve().parent / "repo"))
).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

OMNIROUTE_URL = os.environ.get("OMNIROUTE_BASE_URL", "http://127.0.0.1:20128/v1")
OMNIROUTE_KEY = os.environ.get("OMNIROUTE_API_KEY", "omniroute")
MODEL = os.environ.get("OMNIROUTE_MODEL", "gemini/gemini-3.8-flash")

MAX_STEPS = 25
COMMAND_TIMEOUT = 120
MAX_OUTPUT_CHARS = 15000

BLOCKED = [
    r"\brm\s+-rf\s+/", r"\bsudo\b", r"\bmkfs\b", r"\bshutdown\b",
    r"\breboot\b", r":\(\)\s*\{", r"\bdd\s+if=", r"curl[^|]*\|\s*(sh|bash)",
    r"wget[^|]*\|\s*(sh|bash)", r"\bgit\s+push\b",
]

state = {
    "repo_dir": None,
    "last_failed_command": None,
    "fail_count": 0,
}


def _safe_path(rel_path: str) -> Path:
    if state["repo_dir"] is None:
        raise ValueError("Age clone_repo chalao.")
    base = state["repo_dir"].resolve()
    p = (base / rel_path).resolve()
    if base != p and base not in p.parents:
        raise ValueError("Repo folder er baire access allowed na.")
    return p


def _trim(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n...[output trimmed]"
    return text


# ---------------------------------------------------------------- tools
def clone_repo(url: str) -> str:
    name = url.rstrip("/").split("/")[-1].removesuffix(".git")
    dest = WORKSPACE / name
    if dest.exists():
        state["repo_dir"] = dest
        return f"Repo already ache: {dest}"
    token = os.environ.get("GITHUB_TOKEN")
    clone_url = url
    if token and url.startswith("https://github.com/"):
        clone_url = url.replace("https://", f"https://x-access-token:{token}@")
    
    # Ultra Fast Shallow Clone (--depth 1)
    r = subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, str(dest)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    if r.returncode != 0:
        return "Clone fail: " + r.stderr.replace(token or "NOTOKEN", "***")
    state["repo_dir"] = dest
    return f"Clone hoyeche (Shallow): {dest}"


def list_files(path: str = ".") -> str:
    p = _safe_path(path)
    if not p.is_dir():
        return "Eta folder na."
    items = []
    for child in sorted(p.iterdir()):
        if child.name == ".git":
            continue
        items.append(child.name + ("/" if child.is_dir() else ""))
    return "\n".join(items) or "(khali)"


def read_file(path: str) -> str:
    p = _safe_path(path)
    if not p.is_file():
        return "File paoa jay nai."
    return _trim(p.read_text(encoding="utf-8", errors="replace"))


def write_file(path: str, content: str) -> str:
    p = _safe_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", errors="replace")
    state["fail_count"] = 0
    state["last_failed_command"] = None
    return f"Likha hoyeche: {path} ({len(content)} chars)"


def run_command(command: str) -> str:
    for pattern in BLOCKED:
        if re.search(pattern, command):
            return f"BLOCKED: ei command allowed na ({pattern})"
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            cwd=state["repo_dir"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"Timeout: {COMMAND_TIMEOUT}s er moddhe shesh hoyni."

    if r.returncode != 0:
        if state["last_failed_command"] == command:
            state["fail_count"] += 1
        else:
            state["last_failed_command"] = command
            state["fail_count"] = 1

        if state["fail_count"] >= 3:
            return f"STOP: Ei command-ti por por 3 bar fail hoyeche ({command})."
    else:
        state["last_failed_command"] = None
        state["fail_count"] = 0

    out = f"exit code: {r.returncode}\n--- stdout ---\n{r.stdout}\n--- stderr ---\n{r.stderr}"
    return _trim(out)


AVAILABLE_TOOLS = {
    "clone_repo": clone_repo,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "run_command": run_command,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "clone_repo",
            "description": "Git repository clone kore workspace-e rakhe.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "GitHub repository URL"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Repo ba subfolder-er file list kore.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative folder path", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "File-er puro content pore.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative file path"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "File likhe ba overwrite kore.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path"},
                    "content": {"type": "string", "description": "File er bhetorer text"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Terminal command execute kore repo folder-e.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "PowerShell command"}},
                "required": ["command"],
            },
        },
    },
]

SYSTEM_PROMPT = """Tumi ekta expert coding agent. User tomake ekta GitHub repo ar task dibe.
OS Environment: WINDOWS (Native PowerShell).
Kajer Niyom:
1. Prothome clone_repo chalao.
2. File porar jonno shorashori 'read_file' tool use koro. Linux command (jemon: grep, cat, ls, touch) chalanor cheshta korbe na.
3. Kono command run korte hole shudhu Windows/PowerShell compatible command run koro.
4. Shob kaj sheshe user-er proshner ekta shundor, structured bangla summary dao."""


def call_llm_with_retry(client, messages, max_retries=5):
    """Rate limit ba cooling down ashle auto wait kore abar try korbe."""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
        except Exception as e:
            err_msg = str(e).lower()
            if "429" in err_msg or "cooling down" in err_msg or "rate limit" in err_msg:
                wait_sec = 15 + (attempt * 5)
                print(f"\n[Cooldown / Rate Limit] Gateway cooling down e ache. {wait_sec}s wait kora hocche... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_sec)
            elif "connection" in err_msg:
                print(f"\n[Connection Error] OmniRoute gateway response diche na. 5s por abar cheshta kora hocche...")
                time.sleep(5)
            else:
                raise e
    raise RuntimeError("5 bar cheshtar por-o LLM theke response ashe nai.")


def main():
    if len(sys.argv) < 3:
        print('Usage: python repo_bot.py <repo_url> "<task>"')
        sys.exit(1)
    repo_url, task = sys.argv[1], sys.argv[2]

    client = OpenAI(base_url=OMNIROUTE_URL, api_key=OMNIROUTE_KEY)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Repo: {repo_url}\nTask: {task}"},
    ]

    print(f"OmniRoute gateway-te request pathano hocche ({OMNIROUTE_URL})...")

    for step in range(MAX_STEPS):
        # RPM limit thekate 2.5 second delay
        time.sleep(2.5)

        response = call_llm_with_retry(client, messages)

        choice = response.choices[0]
        msg = choice.message
        messages.append(msg)

        if not msg.tool_calls:
            print("\n===== Final Answer =====")
            print(msg.content)
            return

        for tool_call in msg.tool_calls:
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments or "{}")
            print(f"[tool] {fn_name}({args})")

            tool_fn = AVAILABLE_TOOLS.get(fn_name)
            if tool_fn:
                try:
                    result = tool_fn(**args)
                except Exception as e:
                    result = f"Error: {e}"
            else:
                result = f"Tool '{fn_name}' not found."

            print(f"       -> {str(result)[:150]}...")
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

    print("Max steps exceeded.")


if __name__ == "__main__":
    main()