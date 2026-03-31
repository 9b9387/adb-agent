# ADB Phone Automation Agent

A vision-empowered Android automation agent that allows you to control your mobile device using natural language. Built with the Google Agent Development Kit (ADK) and Gemini, it transforms high-level instructions into precise on-screen actions by "seeing" the device state through screenshots.

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
uv run adk web
```

This will launch a web interface (usually at `http://localhost:8080`) where you can monitor the agent's turns, view screenshots, and inspect the session state in real-time.
