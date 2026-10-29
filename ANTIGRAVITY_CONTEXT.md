# PROJECT: GitHub Repo Automation Agent (Windows Native + OmniRoute)

## 1. Project Overview & Architecture
- Goal: Ekta custom autonomous Python agent (`repo_bot_fixed.py`) toiri kora ja GitHub repository clone, explore, read, command execute ebong task summary korte pare.
- Gateway Architecture:
  - Local Gateway: OmniRoute (`http://127.0.0.1:20128/v1`) port 20128-e running.
  - Protocol: OpenAI-compatible standard API format (`/v1/chat/completions`).
  - Backend LLM: Google Gemini via OmniRoute with dynamic model fallback (`gemini/gemini-flash-lite-latest`, `gemini/gemini-3.1-flash-lite`, `gemini/gemini-3-flash-preview`).
  - Client: Python `openai` library client wrapper.

## 2. Environment & Working Directory
- Platform: Windows 11 Native (PowerShell environment).
- Clone Workspace: `./repo`.

## 3. Core Files & Their Responsibilities
1. `repo_bot_fixed.py`:
   - Ultra-fast shallow clone (`git clone --depth 1`).
   - Tool calling loop: `clone_repo`, `list_files`, `read_file`, `write_file`, `run_command`, `publish_to_github`.
   - Security & Guardrails:
     - Case-insensitive regex blacklist command blocking (e.g., `rm -rf`, `git push`, PowerShell `Remove-Item -Recurse -Force`, `Format-Volume`, `Set-ExecutionPolicy`, etc.).
     - Path traversal restriction (`_safe_path`) preventing directory escape.
     - Environment isolation (`_safe_env`): strips API keys (`GITHUB_TOKEN`, `OMNIROUTE_API_KEY`, `OPENAI_API_KEY`) from child subprocesses.
     - Loop breaker: ekoi failed command por por 3 bar execute hole STOP warning jure deoya hoy.
     - Process tree kill (`taskkill /PID ... /T /F`) timeout-e child process shoho terminate korar jonno.
   - Robustness & Rate-Limit Handling:
     - `call_llm_with_retry`: exponential backoff retry loop on `429`, `cooling down`, or `APIConnectionError`.
     - Model fallback chain: automatically tries lighter/available Gemini models if one hits rate limits.

2. `backtest_repo_bot.py`:
   - Offline end-to-end mock test suite (asol Gemini API key ba internet chhara local git bare repo diye chole).
   - Validates 6 key test suites (total 24 checks passed across Suites A through F).

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
     প্রতিটি অ্যাকশন (Clone, Commit, Dependency Install, Uninstall, Publish) সফল হলো কিনা (Success / Failed), না হলে কেন হয়নি (Reason) সহ সম্পূর্ণ হিস্ট্রি স্বয়ংক্রিয়ভাবে মেইনটেইন করে। `python repo_bot_fixed.py --history` দিয়ে দেখা যায়।

5. `Autonomous GitHub Publisher & Secret Sanitizer (`publish_to_github`):`
   - **Secret Scanning & Sanitization:** কোডবেস স্ক্যান করে যেকোনো হার্ডকোডেড সিক্রেট/টোকেন (OpenAI, GitHub PAT, Google/Gemini, AWS, generic API keys) চিহ্নিত করে। যদি সিক্রেট থাকে, লিক রোধে তৎক্ষণাৎ পুশ বাতিল করে।
   - **Auto-Documentation & Templates:** স্বয়ংক্রিয়ভাবে প্রজেক্টের জন্য কঠোর `.gitignore`, নিরাপদ `.env.example` (স্ক্রাব করা ডামি ভ্যালু সহ), MIT `LICENSE`, এবং প্রফেশনাল `README.md` তৈরি/ভেরিফাই করে।
   - **Pre-Commit Staged Diff Audit:** কমিট করার ঠিক পূর্বে স্টেজড ডিফে কোনো সংবেদনশীল ডেটা আছে কিনা তা ডাবল-চেক করে।
   - **GitHub CLI Integration:** `gh repo create` অথবা `git push` এর মাধ্যমে সরাসরি ইউজারের GitHub অ্যাকাউন্টে পাবলিক বা প্রাইভেট রিপোজিটরি হিসেবে আপলোড করে এবং হিস্ট্রি রেজিস্টারে রেকর্ড যুক্ত করে।
   - **Interactive & Autonomous Access:** CLI (`publish`), চ্যাট ইন্টারফেস, অথবা এলএলএম টুলের মাধ্যমে ব্যবহার করা যায়।

## 4. Current State & Verification
- Status:
  - `repo_bot_fixed.py` is fully verified with Self-Improvement, History Tracking, Permission-based Software Installer, Uninstall, and Autonomous GitHub Publisher & Secret Sanitizer.
  - Published to official GitHub: `https://github.com/New150497/github-repo-bot`
  - `backtest_repo_bot.py` passes all 24/24 checks across all 6 suites (A through F).
