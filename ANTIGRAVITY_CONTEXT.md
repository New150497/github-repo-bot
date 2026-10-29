# PROJECT: GitHub Repo Automation Agent (Windows Native + OmniRoute)

## 1. Project Overview & Architecture
- Goal: Ekta custom autonomous Python agent (`repo_bot_fixed.py`) toiri kora ja GitHub repository clone, explore, read, command execute ebong task summary korte pare[cite: 2].
- Gateway Architecture:
  - Local Gateway: OmniRoute (`http://127.0.0.1:20128/v1`) port 20128-e running[cite: 2].
  - Protocol: OpenAI-compatible standard API format (`/v1/chat/completions`)[cite: 2].
  - Backend LLM: Google Gemini via OmniRoute with dynamic model fallback (`gemini/gemini-flash-lite-latest`, `gemini/gemini-3.1-flash-lite`, `gemini/gemini-3-flash-preview`)[cite: 2].
  - Client: Python `openai` library client wrapper[cite: 2].

## 2. Environment & Working Directory
- Platform: Windows 11 Native (PowerShell environment)[cite: 2].
- Clone Workspace: `./repo`[cite: 2].

## 3. Core Files & Their Responsibilities
1. `repo_bot_fixed.py`:
   - Ultra-fast shallow clone (`git clone --depth 1`)[cite: 2].
   - Tool calling loop: `clone_repo`, `list_files`, `read_file`, `write_file`, `run_command`[cite: 2].
   - Security & Guardrails:
     - Case-insensitive regex blacklist command blocking (e.g., `rm -rf`, `git push`, PowerShell `Remove-Item -Recurse -Force`, `Format-Volume`, `Set-ExecutionPolicy`, etc.)[cite: 2].
     - Path traversal restriction (`_safe_path`) preventing directory escape[cite: 2].
     - Environment isolation (`_safe_env`): strips API keys (`GITHUB_TOKEN`, `OMNIROUTE_API_KEY`, `OPENAI_API_KEY`) from child subprocesses[cite: 2].
     - Loop breaker: ekoi failed command por por 3 bar execute hole STOP warning jure deoya hoy[cite: 2].
     - Process tree kill (`taskkill /PID ... /T /F`) timeout-e child process shoho terminate korar jonno[cite: 2].
   - Robustness & Rate-Limit Handling:
     - `call_llm_with_retry`: exponential backoff retry loop (15s, 20s, 25s...) on `429`, `cooling down`, ba `APIConnectionError`[cite: 2].
     - Step delay (`time.sleep(2.5)`) between turns to respect free tier RPM limits[cite: 2].
     - Windows IPv6 conflict avoid korte explicitly `127.0.0.1` binding[cite: 2].
     - Multi-platform path extraction using `re.split(r"[/\\]", ...)` to prevent Windows backslash parsing bugs[cite: 2].

2. `backtest_repo_bot.py`:
   - Offline end-to-end mock test suite (asol Gemini API key ba internet chhara local git bare repo diye chole)[cite: 1].
   - Validates 6 key test suites (total 23 checks)[cite: 1]:
     - Suite A: Happy Path (test fail -> read -> edit bug -> test pass -> Bangla summary)[cite: 1].
     - Suite B: Mid-run Rate-limit 429 & Connection Error recovery[cite: 1].
     - Suite C: Prompt Injection defense inside README (evaluates blocked malicious commands & secret shielding)[cite: 1].
     - Suite D: Loop trap mitigation on repeated command failures[cite: 1].
     - Suite E: Chaos test (malformed JSON, unknown tools, path traversal escape attempts)[cite: 1].
     - Suite F: Command timeout & orphan child process termination[cite: 1].

3. `Self-Improvement System` (Built directly into `repo_bot_fixed.py`):
   - **Persistent Knowledge Memory (`.bot_lessons.json`):** প্রতি টাস্ক ও এক্সিকিউশন থেকে শেখা অভিজ্ঞতা সংরক্ষণ করে।
   - **Dynamic System Prompt Enhancement (`build_system_prompt`):** বট শুরু হওয়ার সময় পূর্ববর্তী অভিজ্ঞতা ও শিক্ষা স্বয়ংক্রিয়ভাবে প্রম্পটে লোড করে যাতে পুরানো ভুল আর না হয়।
   - **Autonomous Reflection (`reflect_and_learn`):** রান শেষে ট্রাজেক্টরি অ্যানালাইসিস করে কোনো কমান্ড ফেইল ও ফিক্স হলে নিজে নিজেই লেসন এক্সট্র্যাক্ট করে মেমরিতে যুক্ত করে।
   - **In-Loop Learning Tool (`record_lesson`):** এলএলএম এজেন্টের হাতে দেওয়া টুল, যার মাধ্যমে জটিল সমস্যা সমাধানের কৌশল সে নিজেই লিখে রাখতে পারে।
   - **Health Self-Diagnostic (`--self-test`):** `python repo_bot_fixed.py --self-test` কমান্ডের মাধ্যমে যেকোনো সময় বট নিজের স্বাস্থ্য ও ২৪টি চেক ভেরিফাই করতে পারে।

4. `Repository Activity, Dependency Management & Uninstall System`:
   - **Permission-based Dependency/Software Installer (`install_dependency`):**
     প্রজেক্ট রান করার জন্য কোনো ডিপেন্ডেন্সি বা সফটওয়্যার (যেমন: pip প্যাকেজ, npm প্যাকেজ, বা Windows package manager `winget` দিয়ে Java JDK / Node.js) লাগলে ব্যবহারকারীর অনুমতি (Y/N) নিয়ে স্বয়ংক্রিয়ভাবে ইনস্টল করে কোড রান করে দেখায়।
   - **Clean Uninstallation System (`uninstall_repo`):**
     `uninstall <repo_name>` বা চ্যাটে বললে লোকাল ওয়ার্কস্পেস থেকে সম্পূর্ণ ফোল্ডার ডিলিট ও ক্লিন করে।
   - **Persistent History Register ([`.bot_history.json`](file:///d:/NG%20own%20files/Software/Gi%20andd%20git%20hub%20repo/.bot_history.json)):**
     প্রতিটি অ্যাকশন (Clone, Commit, Dependency Install, Uninstall) সফল হলো কিনা (Success / Failed), না হলে কেন হয়নি (Reason) সহ সম্পূর্ণ হিস্ট্রি স্বয়ংক্রিয়ভাবে মেইনটেইন করে। `python repo_bot_fixed.py --history` দিয়ে দেখা যায়।

## 5. Current State & Pending Tasks
- Status:
  - `repo_bot_fixed.py` is fully verified with Self-Improvement, History Tracking, Permission-based Software Installer, and Uninstall feature.
  - `backtest_repo_bot.py` passes all 24/24 checks across all 6 suites (A through F).
- Immediate Next Action:
  - Execute live production agent against target repos:
    `python repo_bot_fixed.py https://github.com/HKUDS/Vibe-Trading "Repo clone kore README.md pore architecture ar setup summary dao"`[cite: 2].