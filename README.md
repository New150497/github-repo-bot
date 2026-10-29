# 🤖 GitHub Repo Automation Agent (`github-repo-bot`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Windows / Linux](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-brightgreen.svg)]()

An autonomous, secure, and self-improving AI coding agent built for Windows & Linux. Give the bot a GitHub repository name or link, and it will automatically clone, inspect the architecture, run tests, fix bugs, manage dependencies with user permission, maintain a commit history register, and deliver structured insights.

---

## ✨ Key Features

- **🔍 Zero-Friction Repository Discovery:**
  - Pass a full GitHub URL (e.g., `https://github.com/octocat/Spoon-Knife`) or simply the project name (e.g., `Spoon-Knife`).
  - The bot automatically queries GitHub's API, resolves the repo, and performs a shallow clone (`--depth 1`).

- **🛡️ Enterprise-Grade Security & Guardrails:**
  - **Command Blacklist:** Destructive operations (`rm -rf`, `git push`, PowerShell `Remove-Item -Recurse -Force`, `Format-Volume`, registry edits) are blocked instantly.
  - **Path Traversal Protection:** Restricts file reading and writing strictly within the cloned repo directory (`_safe_path`).
  - **Secret Shielding:** Sanitizes child process environments (`_safe_env`) to ensure credentials (`GITHUB_TOKEN`, `GEMINI_API_KEY`, etc.) are never leaked.
  - **Anti-Loop Breaker:** Detects repeating command failures and halts stuck loops.
  - **Process Tree Cleanup:** Orphan child processes are cleanly killed on timeout via `taskkill /T /F` or `killpg`.

- **🧠 Self-Improvement & Persistent Memory:**
  - Automatically records reflections and lessons from prior errors into local memory.
  - Dynamically augments its system prompt with relevant past lessons so mistakes are never repeated.

- **📦 Permission-Based Dependency Installer:**
  - Detects missing dependencies or runtimes (Python packages, Node.js/npm packages, or system tools via `winget`).
  - Prompts for explicit user permission (`Y/N`) in the terminal before installing anything.

- **📜 Activity & Commit History Register:**
  - Maintains a persistent record of all handled repositories, commit states, pull request requirements, and uninstalls.
  - Accessible directly in chat or via `--history`.

- **🧹 Clean Uninstallation:**
  - Safely deletes cloned repositories and cleans workspace folders via `uninstall <repo_name>` without file lock crashes.

- **🧪 Built-in 24-Check Verification Suite:**
  - End-to-end offline mock backtest framework (`backtest_repo_bot.py`) that tests resilience, security defense, rate limits, and loop traps without consuming API credits.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Git installed on your system
- An OpenAI-compatible LLM Gateway (e.g., [OmniRoute](https://github.com/omniroute) on `http://127.0.0.1:20128/v1` or any direct OpenAI endpoint)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/New150497/github-repo-bot.git
cd github-repo-bot

# Install required python library
pip install openai
```

### 3. Environment Configuration
Copy the sample environment file:
```powershell
cp .env.example .env
```
*(Optionally adjust `OMNIROUTE_BASE_URL` or `OMNIROUTE_MODEL` inside `.env`)*

---

## 💻 Usage

### Option 1: Double-Click Launcher (Windows)
Double-click `run_bot.bat`. A terminal window will open and prompt you:
```text
👉 GitHub repository-r link/nam dao (ba 'history' / 'uninstall <name>'):
```
Simply type the repository name or paste a URL and press **Enter**!

### Option 2: Command Line
```powershell
# Interactive mode (prompts for repository name)
python repo_bot_fixed.py

# Analyze a repo with automatic discovery
python repo_bot_fixed.py Spoon-Knife

# Custom task execution
python repo_bot_fixed.py https://github.com/HKUDS/Vibe-Trading "README.md pore architecture summary dao"

# Check activity and commit history register
python repo_bot_fixed.py --history

# Uninstall a repository and clean workspace
python repo_bot_fixed.py uninstall Spoon-Knife

# Run the 24-check verification backtest
python repo_bot_fixed.py --self-test
```

---

## 🏛️ Project Architecture

```text
github-repo-bot/
├── repo_bot_fixed.py      # Core autonomous agent & tool orchestrator
├── backtest_repo_bot.py    # 24-check offline verification test suite
├── run_bot.bat             # 1-click Windows launcher
├── .env.example            # Configuration template
├── .gitignore              # Strict ignore rules for safety & clean git state
├── LICENSE                 # MIT License
└── README.md               # Documentation
```

---

## 🧪 Testing & Verification

Run the built-in offline test suite anytime to verify that all 24 safety and logic checks pass:
```powershell
python backtest_repo_bot.py
```
Output:
```text
A) Happy path: test fail -> read -> fix -> test pass -> bangla summary: [PASS]
B) Rate limit + connection error recovery: [PASS]
C) README prompt injection defense: [PASS]
D) Loop trap breaker: [PASS]
E) Chaos & path escape handling: [PASS]
F) Timeout & orphan process termination: [PASS]

Result: 24/24 checks passed
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - Copyright (c) 2026 New150497.
