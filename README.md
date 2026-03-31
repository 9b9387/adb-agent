# ADB Phone Automation Agent

A vision-based Android automation agent built with Google ADK and ADB. The agent accepts a natural-language task, generates a structured plan, then executes it step-by-step by analysing screenshots and issuing ADB commands.

## Architecture

The agent runs in two phases:

**Phase 1 — Planning** (`adb_agent/planner.py`)
A standalone `google.genai` call (outside the ADK loop) produces a JSON plan:
```json
{
  "goal": "...",
  "steps": ["step 1", "step 2", "..."],
  "done_conditions": ["visual condition for step 1", "..."],
  "current_step": 0,
  "completed_observations": []
}
```
The plan is injected into the ADK session state via `create_session(state={"plan": plan})`.

**Phase 2 — Execution** (ADK agent loop)
The agent works through each step one action at a time:
- `before_model_callback` injects the latest screenshot and current plan state into every model turn
- The agent performs **one action per turn** (tap, swipe, type, etc.)
- When the done condition for the current step is visually confirmed, the agent calls `advance_plan(observation)` to move to the next step
- The loop ends when all steps are complete

## Prerequisites

1. Install [uv](https://docs.astral.sh/uv/)
2. Connect an Android device with USB debugging enabled:
   ```bash
   adb devices   # should show your device
   ```
3. Copy the env template and set your API key:
   ```bash
   cp .env.example .env
   # edit .env and set GOOGLE_API_KEY
   ```
4. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

```bash
uv run python main.py "Open the Settings app"
uv run python main.py "Open WeChat and send hello to Alice"
```

The CLI will print the generated plan before execution begins.

## Tools

| Tool | Description |
|------|-------------|
| `advance_plan` | Mark the current step done and move to the next |
| `get_screen_size` | Return screen width and height in pixels |
| `adb_shell` | Run an arbitrary adb shell command |
| `tap` | Tap at coordinates (0–1000 normalised scale) |
| `long_press` | Long-press at coordinates |
| `double_tap` | Double-tap at coordinates |
| `swipe` | Swipe between two coordinates |
| `type_text` | Type text into the focused field |
| `press_keycode` | Send an Android key event (e.g. HOME, BACK) |
| `wait` | Pause for a given number of seconds |
| `push_file` | Upload a file to the device |
| `pull_file` | Download a file from the device |

## Project Structure

```
adb-agent/
├── main.py                 # CLI entry point
├── pyproject.toml
├── adb_agent/
│   ├── agent.py            # ADK agent definition
│   ├── callbacks.py        # before_tool + before_model callbacks
│   ├── planner.py          # Phase 1: standalone plan generation
│   ├── prompts.py          # System prompt
│   └── tools/
│       ├── __init__.py     # ALL_TOOLS export
│       ├── actions.py      # tap, swipe, type_text, adb_shell, …
│       ├── file_ops.py     # push_file, pull_file
│       ├── planning.py     # advance_plan
│       └── screen.py       # screenshot capture + get_screen_size
└── README.md
```
