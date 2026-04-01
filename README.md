# ADB Phone Automation Agent

A vision-empowered Android automation agent that allows you to control your mobile device using natural language. Built with the Google Agent Development Kit (ADK) and Gemini, it transforms high-level instructions into precise on-screen actions by "seeing" the device state through screenshots.

The repository now also includes a separate `browser_agent` that reuses the same plan-first execution architecture, but swaps ADB actions for Playwright tools so the agent can control a desktop browser.

## What can it do?

The agent excels at handling complex, multi-step workflows that require both visual understanding and logical reasoning. 

## How it Works

The agent operates in a two-stage process to ensure reliability and accuracy:

### 1. Planning Phase
When you provide a task, the agent first analyzes the request and breaks it down into a structured, step-by-step plan. Each step includes a specific goal and a "done condition"—a visual state that must be achieved before moving to the next part of the task.

### 2. Execution Phase (Agent Loop)
The agent enters an iterative loop where it:
- **Observes:** Takes a screenshot of the current device screen.
- **Analyzes:** Compares the screenshot with the current step of the plan.
- **Acts:** Selects and executes the most appropriate tool (like a tap or swipe) to progress toward the goal.
- **Validates:** Confirms the action had the intended effect before proceeding.

## Available Tools

The agent is equipped with a versatile set of tools to interact with the device:
- **Touch Actions:** Precision tapping, swiping, and long-pressing based on visual coordinates.
- **Text Input:** Intelligent typing that supports Unicode characters and various languages.
- **System Commands:** Standard navigation like Home, Back, and Recent Apps.
- **Visual Memory:** A "memo" system that allows the agent to store and retrieve data across different steps of a task.
- **File Operations:** Capabilities to push files to the device or pull data from it.
- **Advanced Control:** Direct ADB shell access for low-level system interactions when necessary.

## Getting Started

### Prerequisites
1. **Android Device:** Connected via USB with Developer Options and USB Debugging enabled.
2. **ADB Installed:** The `adb` command must be available in your system PATH.
3. **Environment:** A `.env` file with a valid `GOOGLE_API_KEY`.
4. **Optional - Unicode Support:** For non-ASCII text input (like Chinese), installing [ADBKeyBoard](https://github.com/senzhk/ADBKeyBoard) on the device is recommended.

### Usage
Run the agent by providing your task as a command-line argument:

```bash
uv run python main.py "Open the Settings app and check for system updates"
```

The agent will print its plan and then begin executing the steps while providing real-time feedback on its progress.

### Debugging & Visualization

For a more interactive experience and visual debugging, you can use the ADK Web UI:

```bash
uv run adk-web-agents
```

This launches `adk web` against the dedicated `adk_web_agents/` wrappers so the UI stays focused on the real agents and avoids helper folders like `tests/` or `agent_shared/`. If port `8000` is already occupied, the launcher automatically picks the next free port.

## Browser Agent (Playwright)

The browser agent follows the same overall loop as the phone agent:

1. Generate a structured plan from the user task.
2. Store the plan in ADK session state.
3. Run a loop where the agent observes the current browser page, chooses one tool call, validates progress, and advances the plan with `advance_plan`.

### Browser Setup

Install the Python dependency and Playwright's Chromium browser:

```bash
uv sync
uv run playwright install chromium
```

Recommended `.env` settings:

```bash
GOOGLE_API_KEY=your-api-key
MODEL_NAME=gemini-3-flash-preview
BROWSER_CDP_URL=
BROWSER_USER_DATA_DIR=.browser-profile/playwright
BROWSER_HEADLESS=false
BROWSER_CHANNEL=
BROWSER_START_URL=
```

### Reuse Your Current Browser via CDP

Yes. If you want the agent to drive your already running Chrome or Chromium instead of opening its own Playwright profile, start that browser with a remote debugging port and set `BROWSER_CDP_URL`.

Example:

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

Then in `.env`:

```bash
BROWSER_CDP_URL=http://127.0.0.1:9222
```

When `BROWSER_CDP_URL` is set, `browser_agent` will:

- connect to the existing browser over CDP
- reuse the current browser session and logged-in tabs
- avoid closing your real browser when the agent disconnects

If `BROWSER_CDP_URL` is not set, it falls back to the dedicated persistent Playwright profile.

### Browser Usage

Run the browser agent with a natural-language task:

```bash
uv run browser-agent "Open GitHub, search for google/adk, and stop when the repository page is visible"
```

You can also call the entrypoint directly:

```bash
uv run python browser_main.py "Open Hacker News and search for Playwright posts"
```

### Persistent Profile Notes

- Default mode uses a persistent Playwright context so login state can survive across runs.
- By default it uses `.browser-profile/playwright` inside the repo. This is the safest option for automation.
- CDP mode is better if you explicitly want to drive your already running browser.
- A dedicated automation profile is still strongly recommended for non-CDP usage. Reusing your day-to-day browser profile can fail because of profile locking and can pollute your normal browsing session.

### ADK Web Usage

To debug both agents in the ADK Web UI:

```bash
uv run adk-web-agents
```

If you want to force a specific port, you still can:

```bash
uv run adk-web-agents --port 8093
```

`adk web` itself expects a directory whose subdirectories each contain `__init__.py` and `agent.py`. This repo provides lightweight wrappers under `adk_web_agents/` so the UI only lists the real `adb_agent` and `browser_agent`.
