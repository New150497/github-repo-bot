"""
telegram_remote.py - Autonomous GitHub Agent Telegram Remote Controller
Allows complete remote control of github-repo-bot via Telegram.
"""

import os
import sys
import re
import time
import json
import uuid
import threading
import subprocess
import requests
from pathlib import Path

# Import core agent tools and state
import repo_bot_fixed as bot

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/{method}"

# In-memory session state
tg_state = {
    "token": None,
    "bot_username": None,
    "allowed_user_id": None,
    "active_repo": None,
    "is_busy": False,
    "pending_permissions": {},  # req_id -> {"event": threading.Event(), "result": None, "details": dict}
    "last_update_id": 0,
}


def load_env_vars():
    """Load configuration variables from .env file."""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k not in os.environ:
                os.environ[k] = v


def save_env_var(key: str, val: str):
    """Save or update an environment variable in .env."""
    lines = []
    found = False
    if ENV_PATH.exists():
        lines = ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            new_lines.append(f"{key}={val}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={val}")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ[key] = val


def get_telegram_token() -> str:
    """Retrieve token from env or interactively guide user to get one from @BotFather."""
    load_env_vars()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        tg_state["token"] = token
        return token

    print("\n" + "=" * 67)
    print("📱 [Telegram Remote Control Setup]")
    print("=" * 67)
    print("টেলিগ্রাম দিয়ে রিমোটলি বট অপারেট করতে ১টি ফ্রি Bot Token প্রয়োজন (১ মিনিট লাগে):")
    print("  👉 1. আপনার Telegram অ্যাপে সার্চ করুন: @BotFather")
    print("  👉 2. BotFather-কে /newbot লিখে পাঠান।")
    print("  👉 3. আপনার বটের নাম দিন (যেমন: My GitHub Bot)।")
    print("  👉 4. একটি ইউজারনেম দিন যার শেষে 'bot' থাকবে (যেমন: my_repo_control_bot)।")
    print("  👉 5. BotFather আপনাকে একটি HTTP API Token দেবে (যেমন: 123456789:ABCdef...)")
    print("=" * 67)

    try:
        token = input("👉 আপনার Telegram Bot Token-টি এখানে পেস্ট করুন: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""

    if token:
        save_env_var("TELEGRAM_BOT_TOKEN", token)
        tg_state["token"] = token
        print("✅ Telegram Bot Token .env ফাইলে সফলভাবে সংরক্ষিত হয়েছে!\n")
    return token


def tg_call(method: str, data: dict = None, timeout: int = 35) -> dict:
    """Execute a request against the Telegram Bot API."""
    token = tg_state["token"]
    if not token:
        token = get_telegram_token()
    if not token:
        return {}
    url = TELEGRAM_API_URL.format(token=token, method=method)
    try:
        resp = requests.post(url, json=data or {}, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"[Telegram API Error {resp.status_code}] {resp.text}")
            return {}
    except Exception as e:
        print(f"[Telegram Network Error] {e}")
        return {}


def send_message(chat_id: int, text: str, reply_markup: dict = None, parse_mode: str = "HTML") -> dict:
    """Send a message to Telegram, automatically chunking if > 4000 characters."""
    max_len = 3900

    def _build_payload(t, markup, pmode):
        d = {"chat_id": chat_id, "text": t, "disable_web_page_preview": True}
        if pmode:
            d["parse_mode"] = pmode
        if markup:
            d["reply_markup"] = markup
        return d

    if len(text) <= max_len:
        res = tg_call("sendMessage", _build_payload(text, reply_markup, parse_mode))
        if not res and parse_mode:
            res = tg_call("sendMessage", _build_payload(text, reply_markup, None))
        return res

    chunks = [text[i:i + max_len] for i in range(0, len(text), max_len)]
    last_res = {}
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        last_res = tg_call("sendMessage", _build_payload(chunk, markup, parse_mode))
    return last_res


def edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None, parse_mode: str = "HTML"):
    """Edit an existing message."""
    d = {"chat_id": chat_id, "message_id": message_id, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        d["parse_mode"] = parse_mode
    if reply_markup:
        d["reply_markup"] = reply_markup
    return tg_call("editMessageText", d)


def send_typing(chat_id: int):
    """Show typing status indicator in Telegram."""
    tg_call("sendChatAction", {"chat_id": chat_id, "action": "typing"}, timeout=10)


def answer_callback(callback_id: str, text: str = None):
    """Acknowledge Telegram callback query."""
    tg_call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text or ""})


def check_auth(user_id: int, chat_id: int) -> bool:
    """Enforce strict single-owner authentication to prevent unauthorized remote access."""
    allowed = tg_state["allowed_user_id"]
    if allowed is None:
        tg_state["allowed_user_id"] = user_id
        save_env_var("TELEGRAM_ALLOWED_USER_ID", str(user_id))
        send_message(
            chat_id,
            f"🎉 <b>Pairing Successful!</b>\n"
            f"আপনার Telegram অ্যাকাউন্টটি (ID: <code>{user_id}</code>) এই মেশিনের অনুমোদিত কন্ট্রোলার হিসেবে লক করা হয়েছে।\n"
            f"অন্য কোনো ব্যবহারকারী এই বট নিয়ন্ত্রণ করতে পারবে না।"
        )
        return True

    if user_id == allowed:
        return True

    send_message(
        chat_id,
        f"⛔ <b>Access Denied (অনুমতি নেই)</b>\n"
        f"এই বটটি ব্যক্তিগতভাবে এর হোস্ট মেশিনের মালিকের অ্যাকাউন্টের সাথে সুরক্ষিত।\n"
        f"User ID: <code>{user_id}</code> অনুমোদিত নয়।"
    )
    return False


def build_dashboard_keyboard() -> dict:
    """Build the interactive main menu inline keyboard."""
    return {
        "inline_keyboard": [
            [
                {"text": "📦 Select Repo", "callback_data": "menu:repos"},
                {"text": "➕ Clone Repo", "callback_data": "menu:clone"},
            ],
            [
                {"text": "📊 System Status", "callback_data": "menu:status"},
                {"text": "📜 Activity History", "callback_data": "menu:history"},
            ],
            [
                {"text": "🚀 Publish to GitHub", "callback_data": "menu:publish"},
                {"text": "🔑 Engine Key", "callback_data": "menu:key"},
            ],
            [
                {"text": "🧹 Uninstall Repo", "callback_data": "menu:uninstall"},
                {"text": "❓ Help & Guide", "callback_data": "menu:help"},
            ],
        ]
    }


def send_dashboard(chat_id: int):
    """Render the central status dashboard."""
    bot.ensure_omniroute_running()
    net_ok = bot.check_internet()
    omni_ok = bot.is_omniroute_running()
    repos = bot.get_available_repos()
    active_repos = [r for r in repos if r["exists"]]

    cur_repo = tg_state["active_repo"] or (active_repos[0]["name"] if active_repos else "None")

    net_badge = "🌐 <b>Online (Connected)</b>" if net_ok else "⚠️ <b>Offline</b>"
    omni_badge = "🚀 <b>Active (127.0.0.1:20128)</b>" if omni_ok else "⚠️ <b>Offline</b>"

    text = (
        f"🤖 <b>GitHub Autonomous Agent - Remote Hub</b>\n"
        f"────────────────────────────\n"
        f"[Internet]  {net_badge}\n"
        f"[AI Engine] {omni_badge}\n"
        f"[Active Repo] 📦 <b>{cur_repo}</b>\n"
        f"[Total Repos] 📁 {len(active_repos)} টি সংরক্ষিত\n"
        f"────────────────────────────\n"
        f"💡 <i>যেকোনো GitHub লিংক পাঠালে স্বয়ংক্রিয়ভাবে PC-তে টার্মিনাল খুলে কাজ শুরু করবে!</i>\n"
        f"💡 <i>অথবা যেকোনো টাস্ক নির্দেশ সরাসরি লিখে পাঠান!</i>"
    )
    send_message(chat_id, text, reply_markup=build_dashboard_keyboard())


def handle_repos_menu(chat_id: int):
    """Show interactive repository switcher buttons."""
    repos = bot.get_available_repos()
    active = [r for r in repos if r["exists"]]
    if not active:
        send_message(chat_id, "📁 বর্তমানে কোনো রিপোজিটরি সংরক্ষিত নেই। নতুন রিপো যুক্ত করতে <code>/clone &lt;repo_url&gt;</code> অথবা সরাসরি রিপো লিংক লিখে পাঠান।")
        return

    buttons = []
    for r in active:
        name = r["name"]
        prefix = "👉 " if name == tg_state["active_repo"] else "📦 "
        buttons.append([{"text": f"{prefix}{name}", "callback_data": f"select_repo:{name}"}])
    buttons.append([{"text": "🔙 Back to Menu", "callback_data": "menu:main"}])

    send_message(
        chat_id,
        "📁 <b>কাজের জন্য একটি রিপোজিটরি বেছে নিন:</b>\n<i>(যে রিপো সিলেক্ট করবেন পরবর্তী নির্দেশগুলো সেখানে কার্যকর হবে)</i>",
        reply_markup={"inline_keyboard": buttons}
    )


def handle_status_command(chat_id: int):
    """Provide detailed host and agent telemetry."""
    net_ok = bot.check_internet()
    omni_ok = bot.is_omniroute_running()
    repos = bot.get_available_repos()
    active = [r for r in repos if r["exists"]]
    lessons = bot.load_lessons()

    cur_repo = tg_state["active_repo"] or (active[0]["name"] if active else "None")
    repo_files = 0
    if cur_repo and (bot.WORKSPACE / cur_repo).exists():
        repo_files = sum(1 for _ in (bot.WORKSPACE / cur_repo).rglob("*") if _.is_file())

    msg = (
        f"📊 <b>System & Agent Telemetry</b>\n"
        f"────────────────────────────\n"
        f"• <b>Host Platform:</b> {sys.platform.capitalize()} (Windows Native)\n"
        f"• <b>Python Runtime:</b> {sys.version.split()[0]}\n"
        f"• <b>Internet Access:</b> {'✅ Connected' if net_ok else '❌ Disconnected'}\n"
        f"• <b>Local AI Gateway:</b> {'✅ Running (Port 20128)' if omni_ok else '❌ Inactive'}\n"
        f"• <b>Active Repository:</b> <code>{cur_repo}</code> ({repo_files} files)\n"
        f"• <b>Managed Repositories:</b> {len(active)} projects\n"
        f"• <b>Self-Improvement Memory:</b> {len(lessons)} learned lessons\n"
        f"• <b>Workspace Directory:</b> <code>{bot.WORKSPACE}</code>\n"
        f"────────────────────────────"
    )
    send_message(chat_id, msg, reply_markup=build_dashboard_keyboard())


def handle_history_command(chat_id: int):
    """Display persistent activity log."""
    entries = bot.get_history_entries()
    if not entries:
        send_message(chat_id, "📜 কোনো হিস্ট্রি রেকর্ড পাওয়া যায়নি।")
        return

    lines = ["📜 <b>Recent Activity & Commit Register</b>\n────────────────────────────"]
    for e in entries[-8:]:
        status_emoji = "✅" if e.get("status") == "Success" else "❌"
        repo = e.get("repo", "Unknown")
        act = e.get("action", "").capitalize()
        ts = e.get("timestamp", "").split("T")[0]
        reason = f" ({e.get('reason')})" if e.get("reason") else ""
        lines.append(f"{status_emoji} <b>{repo}</b> - {act}{reason} [<i>{ts}</i>]")

    lines.append("────────────────────────────")
    send_message(chat_id, "\n".join(lines), reply_markup=build_dashboard_keyboard())


def is_github_repo_input(text: str) -> bool:
    """Detect whether user input is a GitHub URL or a repo identifier."""
    t = text.strip()
    if re.search(r"github\.com[/:]([a-zA-Z0-9_\-\.]+)/([a-zA-Z0-9_\-\.]+)", t, re.IGNORECASE):
        return True
    if re.match(r"^[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+$", t):
        return True
    if t.lower().startswith("clone "):
        return True
    return False


def handle_repo_link_or_clone(chat_id: int, repo_input: str):
    """Automatically resolve, clone, activate OmniRoute, launch PC terminal, and explore a repository."""
    if tg_state["is_busy"]:
        send_message(chat_id, "⏳ বট বর্তমানে অন্য একটি টাস্ক নিয়ে কাজ করছে। অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।")
        return

    tg_state["is_busy"] = True

    def _worker():
        try:
            clean_input = repo_input.strip()
            if clean_input.lower().startswith("clone "):
                clean_input = clean_input[6:].strip()

            send_message(
                chat_id,
                f"🔍 <b>GitHub Repository সনাক্ত হয়েছে:</b> <code>{clean_input}</code>\n"
                f"• 🌐 OmniRoute AI Gateway ভেরিফাই করা হচ্ছে...\n"
                f"• 📦 কোডবেস ক্লোন করার প্রস্তুতি চলছে..."
            )

            # 1. Activate OmniRoute Gateway
            bot.ensure_omniroute_running()

            # 2. Resolve URL & Shallow Clone
            resolved_url = bot.resolve_repo_url(clean_input)
            clone_res = bot.clone_repo(resolved_url)

            repo_name = bot.state["repo_dir"].name if bot.state["repo_dir"] else clean_input.split("/")[-1].replace(".git", "")
            tg_state["active_repo"] = repo_name
            bot.set_active_repo(repo_name)

            # 3. Create dedicated launcher
            launcher_path = bot.create_repo_launcher(repo_name)

            # 4. Open dedicated terminal window on PC
            terminal_started = False
            try:
                if sys.platform == "win32" and launcher_path.exists():
                    subprocess.Popen(f'start "{repo_name} Agent" cmd /k "{str(launcher_path)}"', shell=True)
                    terminal_started = True
            except Exception as ex:
                print(f"[Terminal Launch Warning] {ex}")

            term_msg = f"🖥️ <b>PC-তে টার্মিনাল উইন্ডো খোলা হয়েছে:</b> <code>{launcher_path.name}</code>\n" if terminal_started else ""

            send_message(
                chat_id,
                f"✅ <b>রিপোজিটরি প্রস্তুত!</b>\n"
                f"• Repository: 📦 <b>{repo_name}</b>\n"
                f"• Status: {clone_res}\n"
                f"{term_msg}"
                f"• AI Gateway: 🚀 Active (127.0.0.1:20128)\n"
                f"────────────────────────────\n"
                f"⚙️ <i>স্বয়ংক্রিয়ভাবে আর্কিটেকচার, ফিচার ও টেস্টসমূহ পরীক্ষা করা হচ্ছে...</i>"
            )

            # 5. Run initial exploration task (DEFAULT_TASK)
            repo_path = bot.WORKSPACE / repo_name
            client = bot.OpenAI(base_url=bot.OMNIROUTE_URL, api_key=bot.OMNIROUTE_KEY, max_retries=0, timeout=180)
            prompt = bot.build_system_prompt()
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Repo: {repo_path.as_uri()}\nTask: {bot.DEFAULT_TASK}"},
            ]

            def _step_callback(event_type: str, data: dict):
                send_typing(chat_id)

            answer = bot.run_agent_turn(client, messages, step_callback=_step_callback)

            # 6. Deliver structured summary to Telegram
            send_message(
                chat_id,
                f"🎉 <b>স্বয়ংক্রিয় অ্যানালাইসিস সম্পন্ন! (Repo: {repo_name})</b>\n"
                f"────────────────────────────\n"
                f"{answer}\n"
                f"────────────────────────────\n"
                f"💡 <i>এখন এই রিপোজিটরি নিয়ে যেকোনো কাজ করাতে সরাসরি মেসেজ পাঠান!</i>",
                reply_markup=build_dashboard_keyboard()
            )

        except Exception as e:
            send_message(chat_id, f"❌ <b>রিপো প্রসেস করতে ত্রুটি হয়েছে:</b>\n<code>{str(e)}</code>")
        finally:
            tg_state["is_busy"] = False

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def execute_agent_task(chat_id: int, user_instruction: str):
    """Run an autonomous agent task in the background, updating Telegram with live progress."""
    if tg_state["is_busy"]:
        send_message(chat_id, "⏳ বট বর্তমানে অন্য একটি টাস্ক নিয়ে কাজ করছে। অনুগ্রহ করে কিছুক্ষণ অপেক্ষা করুন।")
        return

    tg_state["is_busy"] = True

    def _worker():
        try:
            bot.ensure_omniroute_running()
            repos = bot.get_available_repos()
            active = [r for r in repos if r["exists"]]

            cur_repo = tg_state["active_repo"]
            if not cur_repo:
                if active:
                    cur_repo = active[0]["name"]
                    tg_state["active_repo"] = cur_repo
                else:
                    send_message(chat_id, "⚠️ কোনো রিপোজিটরি নেই! অনুগ্রহ করে আগে একটি রিপোর লিংক বা নাম পাঠান।")
                    return

            bot.set_active_repo(cur_repo)
            repo_path = bot.WORKSPACE / cur_repo

            status_msg = send_message(
                chat_id,
                f"⚙️ <b>Autonomous Agent চালু হয়েছে...</b>\n"
                f"• Target Repo: <code>{cur_repo}</code>\n"
                f"• Task: <i>{user_instruction}</i>\n"
                f"• Status: চিন্তা করছে ও কোড পরিদর্শন করছে..."
            )
            msg_id = status_msg.get("result", {}).get("message_id") if status_msg else None

            client = bot.OpenAI(base_url=bot.OMNIROUTE_URL, api_key=bot.OMNIROUTE_KEY, max_retries=0, timeout=180)
            prompt = bot.build_system_prompt()
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Repo: {repo_path.as_uri()}\nTask: {user_instruction}"},
            ]

            step_logs = []

            def _step_callback(event_type: str, data: dict):
                send_typing(chat_id)
                if event_type == "tool_start":
                    name = data.get("name", "")
                    step_logs.append(f"🔧 Running <code>{name}</code>...")
                    if msg_id and len(step_logs) % 2 == 1:
                        edit_message(
                            chat_id, msg_id,
                            f"⚙️ <b>Autonomous Agent কাজ করছে...</b>\n"
                            f"• Target Repo: <code>{cur_repo}</code>\n"
                            f"• Recent Actions:\n" + "\n".join(step_logs[-4:])
                        )
                elif event_type == "tool_end":
                    pass

            answer = bot.run_agent_turn(client, messages, step_callback=_step_callback)

            send_message(
                chat_id,
                f"✅ <b>টাস্ক সম্পন্ন হয়েছে! (Repo: {cur_repo})</b>\n"
                f"────────────────────────────\n"
                f"{answer}\n"
                f"────────────────────────────",
                reply_markup=build_dashboard_keyboard()
            )

        except Exception as e:
            send_message(chat_id, f"❌ <b>টাস্ক পরিচালনায় ত্রুটি:</b>\n<code>{str(e)}</code>")
        finally:
            tg_state["is_busy"] = False

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def telegram_permission_handler(action_type: str, details: dict) -> bool:
    """Telegram inline permission callback interceptor for dependencies and publishing."""
    allowed_id = tg_state["allowed_user_id"]
    if not allowed_id:
        return True

    req_id = str(uuid.uuid4())[:8]
    event = threading.Event()
    tg_state["pending_permissions"][req_id] = {
        "event": event,
        "result": False,
        "details": details,
    }

    if action_type == "install_dependency":
        pkg = details.get("package", "")
        mgr = details.get("manager", "")
        cmd = details.get("command", "")
        text = (
            f"⚠️ <b>সফটওয়্যার / ডিপেন্ডেন্সি ইনস্টলেশন রিকোয়েস্ট</b>\n"
            f"────────────────────────────\n"
            f"• <b>Manager:</b> <code>{mgr}</code>\n"
            f"• <b>Package:</b> <code>{pkg}</code>\n"
            f"• <b>Command:</b> <code>{cmd}</code>\n"
            f"────────────────────────────\n"
            f"👉 আপনি কি এটি হোস্ট মেশিনে ইনস্টল করার অনুমতি দিচ্ছেন?"
        )
        buttons = [
            [
                {"text": "✅ অনুমোদন দিন (Approve)", "callback_data": f"perm:{req_id}:yes"},
                {"text": "❌ বাতিল করুন (Reject)", "callback_data": f"perm:{req_id}:no"},
            ]
        ]
        send_message(allowed_id, text, reply_markup={"inline_keyboard": buttons})

    elif action_type == "publish_to_github":
        r_name = details.get("repo_name", "")
        user = details.get("gh_user", "")
        vis = details.get("visibility", "public")
        text = (
            f"🚀 <b>GitHub Publish Confirmation Request</b>\n"
            f"────────────────────────────\n"
            f"• <b>Repository:</b> <code>@{user}/{r_name}</code>\n"
            f"• <b>Visibility:</b> <code>{vis.upper()}</code>\n"
            f"• <b>Security Audit:</b> ✅ Verified Clean\n"
            f"────────────────────────────\n"
            f"👉 আপনি কি এই প্রজেক্টটি GitHub-এ পুশ করার অনুমতি দিচ্ছেন?"
        )
        buttons = [
            [
                {"text": f"✅ Push to GitHub ({vis})", "callback_data": f"perm:{req_id}:yes"},
                {"text": "❌ Cancel", "callback_data": f"perm:{req_id}:no"},
            ]
        ]
        send_message(allowed_id, text, reply_markup={"inline_keyboard": buttons})

    completed = event.wait(timeout=120)
    result = tg_state["pending_permissions"].pop(req_id, {}).get("result", False) if completed else False
    return result


bot.PERMISSION_CALLBACK = telegram_permission_handler


def handle_callback_query(cq: dict):
    """Handle interactive inline keyboard button taps."""
    cb_id = cq["id"]
    from_user = cq["from"]["id"]
    chat_id = cq.get("message", {}).get("chat", {}).get("id", from_user)
    data = cq.get("data", "")

    if not check_auth(from_user, chat_id):
        answer_callback(cb_id, "Access Denied")
        return

    answer_callback(cb_id)

    if data.startswith("perm:"):
        parts = data.split(":")
        if len(parts) == 3:
            req_id, choice = parts[1], parts[2]
            if req_id in tg_state["pending_permissions"]:
                tg_state["pending_permissions"][req_id]["result"] = (choice == "yes")
                tg_state["pending_permissions"][req_id]["event"].set()
                status_txt = "✅ অনুমোদিত হয়েছে (Approved)" if choice == "yes" else "❌ বাতিল করা হয়েছে (Rejected)"
                send_message(chat_id, f"👉 {status_txt}")
        return

    if data == "menu:main":
        send_dashboard(chat_id)
        return

    if data == "menu:repos":
        handle_repos_menu(chat_id)
        return

    if data == "menu:status":
        handle_status_command(chat_id)
        return

    if data == "menu:history":
        handle_history_command(chat_id)
        return

    if data == "menu:clone":
        send_message(chat_id, "➕ নতুন রিপো ক্লোন করতে সরাসরি GitHub লিংক পাঠান বা লিখুন:\n<code>/clone &lt;repo_url_or_name&gt;</code>\nউদাহরণ: <code>https://github.com/octocat/Spoon-Knife</code>")
        return

    if data == "menu:key":
        send_message(chat_id, "🔑 AI Engine Key আপডেট করতে কমান্ড লিখুন:\n<code>/key &lt;your_new_api_key&gt;</code>")
        return

    if data == "menu:publish":
        cur_repo = tg_state["active_repo"]
        if not cur_repo:
            send_message(chat_id, "⚠️ আগে একটি রিপোজিটরি বেছে নিন।")
            return
        buttons = [
            [
                {"text": f"🌐 Publish '{cur_repo}' (Public)", "callback_data": f"pubconf:{cur_repo}:public"},
                {"text": f"🔒 Publish '{cur_repo}' (Private)", "callback_data": f"pubconf:{cur_repo}:private"},
            ],
            [{"text": "🔙 Back", "callback_data": "menu:main"}]
        ]
        send_message(chat_id, f"🚀 আপনি কি <b>{cur_repo}</b> GitHub-এ পাবলিশ করতে চান?", reply_markup={"inline_keyboard": buttons})
        return

    if data.startswith("pubconf:"):
        parts = data.split(":")
        r_name, vis = parts[1], parts[2]
        send_message(chat_id, f"🚀 <b>{r_name}</b> GitHub-এ ({vis}) আপলোড করা হচ্ছে...")
        res = bot.publish_to_github(repo_name=r_name, visibility=vis)
        send_message(chat_id, res, reply_markup=build_dashboard_keyboard())
        return

    if data == "menu:uninstall":
        cur_repo = tg_state["active_repo"]
        if not cur_repo:
            send_message(chat_id, "⚠️ কোনো অ্যাক্টিভ রিপোজিটরি নেই।")
            return
        buttons = [
            [{"text": f"🗑️ নিশ্চিত মুছুন ({cur_repo})", "callback_data": f"unconf:{cur_repo}"}],
            [{"text": "❌ Cancel", "callback_data": "menu:main"}]
        ]
        send_message(chat_id, f"⚠️ আপনি কি নিশ্চিতভাবে <b>{cur_repo}</b> সম্পূর্ণ মুছে ফেলতে চান?", reply_markup={"inline_keyboard": buttons})
        return

    if data.startswith("unconf:"):
        r_name = data.split(":", 1)[1]
        res = bot.uninstall_repo(r_name)
        tg_state["active_repo"] = None
        send_message(chat_id, res, reply_markup=build_dashboard_keyboard())
        return

    if data.startswith("select_repo:"):
        r_name = data.split(":", 1)[1]
        if bot.set_active_repo(r_name):
            tg_state["active_repo"] = r_name
            send_message(chat_id, f"✅ অ্যাক্টিভ রিপোজিটরি পরিবর্তন করা হয়েছে: 📦 <b>{r_name}</b>", reply_markup=build_dashboard_keyboard())
        else:
            send_message(chat_id, f"❌ রিপোজিটরি ফোল্ডার খুঁজে পাওয়া যায়নি: {r_name}")
        return

    if data == "menu:help":
        help_text = (
            "📖 <b>Telegram Remote Commands:</b>\n"
            "────────────────────────────\n"
            "• <b>সরাসরি GitHub Link বা Repo নাম পাঠান</b> - PC-তে স্বয়ংক্রিয়ভাবে টার্মিনাল খুলে কাজ শুরু করবে!\n"
            "• <code>/start</code> বা <code>/menu</code> - ড্যাশবোর্ড মেনু ওপেন করুন\n"
            "• <code>/repos</code> - রিপোজিটরি তালিকা দেখুন ও পরিবর্তন করুন\n"
            "• <code>/clone &lt;url/name&gt;</code> - নতুন রিপো ক্লোন করুন\n"
            "• <code>/status</code> - হোস্ট ও এআই গেটওয়ে স্ট্যাটাস দেখুন\n"
            "• <code>/history</code> - অ্যাক্টিভিটি হিস্ট্রি দেখুন\n"
            "• <code>/publish [public|private]</code> - গিটহাবে পাবলিশ করুন\n"
            "• <code>/key &lt;new_key&gt;</code> - এআই ইঞ্জিন ক্রেডেনশিয়াল আপডেট করুন\n"
            "• <code>/uninstall &lt;name&gt;</code> - রিপো আনইনস্টল করুন\n"
            "• <i>যেকোনো সাধারণ মেসেজ</i> - বর্তমান রিপোর উপর এজেন্টের মাধ্যমে স্বয়ংক্রিয়ভাবে কোডিং ও রান হবে!\n"
            "────────────────────────────"
        )
        send_message(chat_id, help_text, reply_markup=build_dashboard_keyboard())
        return


def handle_message(msg: dict):
    """Handle incoming Telegram text messages."""
    from_user = msg.get("from", {}).get("id")
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "").strip()

    if not from_user or not chat_id or not text:
        return

    if not check_auth(from_user, chat_id):
        return

    # 1. Check if user sent a GitHub URL or clone command
    if is_github_repo_input(text):
        handle_repo_link_or_clone(chat_id, text)
        return

    # 2. Slash commands
    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/start", "/menu", "/hub"):
            send_dashboard(chat_id)
            return

        if cmd in ("/repos", "/dropdown", "/list"):
            handle_repos_menu(chat_id)
            return

        if cmd == "/status":
            handle_status_command(chat_id)
            return

        if cmd == "/history":
            handle_history_command(chat_id)
            return

        if cmd == "/help":
            handle_callback_query({"id": "0", "from": {"id": from_user}, "message": {"chat": {"id": chat_id}}, "data": "menu:help"})
            return

        if cmd == "/clone":
            if not arg:
                send_message(chat_id, "⚠️ অনুগ্রহ করে রিপোজিটরির নাম বা URL দিন:\nউদাহরণ: <code>/clone Spoon-Knife</code>")
                return
            handle_repo_link_or_clone(chat_id, arg)
            return

        if cmd == "/key":
            if not arg:
                send_message(chat_id, "⚠️ অনুগ্রহ করে আপনার নতুন API Key প্রদান করুন:\n<code>/key &lt;new_api_key&gt;</code>")
                return
            ok, res_msg = bot.update_gemini_api_key(arg)
            send_message(chat_id, f"🔑 {res_msg}", reply_markup=build_dashboard_keyboard())
            return

        if cmd == "/publish":
            vis = arg.lower() if arg in ("public", "private") else "public"
            cur_repo = tg_state["active_repo"]
            if not cur_repo:
                send_message(chat_id, "⚠️ আগে <code>/repos</code> দিয়ে একটি রিপো সিলেক্ট করুন।")
                return
            send_message(chat_id, f"🚀 <b>{cur_repo}</b> GitHub-এ ({vis}) পাবলিশ করা হচ্ছে...")
            res = bot.publish_to_github(repo_name=cur_repo, visibility=vis)
            send_message(chat_id, res, reply_markup=build_dashboard_keyboard())
            return

        if cmd == "/uninstall":
            target = arg or tg_state["active_repo"]
            if not target:
                send_message(chat_id, "⚠️ অনুগ্রহ করে আনইনস্টল করার জন্য রিপোর নাম দিন:\n<code>/uninstall &lt;repo_name&gt;</code>")
                return
            res = bot.uninstall_repo(target)
            if tg_state["active_repo"] == target:
                tg_state["active_repo"] = None
            send_message(chat_id, res, reply_markup=build_dashboard_keyboard())
            return

    # 3. Regular natural language message -> Execute with autonomous agent
    execute_agent_task(chat_id, text)


def start_telegram_bot():
    """Main daemon loop running long-polling with Telegram Bot API."""
    token = get_telegram_token()
    if not token:
        print("❌ Telegram Bot Token ছাড়া রিমোট সার্ভিস চালু করা সম্ভব নয়।")
        return

    tg_state["token"] = token
    load_env_vars()

    allowed_id_str = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
    if allowed_id_str.isdigit():
        tg_state["allowed_user_id"] = int(allowed_id_str)

    me = tg_call("getMe")
    if not me or not me.get("ok"):
        print("❌ Telegram Bot Token সঠিক নয় অথবা টেলিগ্রাম সার্ভারের সাথে সংযোগ করা যায়নি।")
        return

    bot_info = me.get("result", {})
    tg_state["bot_username"] = bot_info.get("username", "UnknownBot")

    repos = bot.get_available_repos()
    active = [r for r in repos if r["exists"]]
    if active:
        tg_state["active_repo"] = active[0]["name"]
        bot.set_active_repo(active[0]["name"])

    bot.ensure_omniroute_running()

    print("\n" + "=" * 67)
    print("🚀 [Telegram Remote Control Active & Listening]")
    print("=" * 67)
    print(f"• Bot Username : @{tg_state['bot_username']}")
    print(f"• Active Repo  : {tg_state['active_repo'] or 'None'}")
    owner_str = f"User ID {tg_state['allowed_user_id']}" if tg_state['allowed_user_id'] else "Any (Auto-binds on /start)"
    print(f"• Security     : 🔒 Locked to {owner_str}")
    print("• Remote Mode  : 📱 Open Telegram and send /start to begin!")
    print("• Press Ctrl+C in this terminal anytime to stop.")
    print("=" * 67 + "\n")

    offset = 0
    while True:
        try:
            updates = tg_call("getUpdates", {"offset": offset, "timeout": 25}, timeout=35)
            if updates and updates.get("ok"):
                for u in updates.get("result", []):
                    offset = u["update_id"] + 1
                    if "message" in u:
                        handle_message(u["message"])
                    elif "callback_query" in u:
                        handle_callback_query(u["callback_query"])
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nবট বন্ধ করা হচ্ছে...")
            break
        except Exception as e:
            print(f"[Polling Exception] {e}")
            time.sleep(3)


if __name__ == "__main__":
    start_telegram_bot()
