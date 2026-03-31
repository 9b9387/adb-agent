"""Quick verification script."""
try:
    from adb_agent.tools.planning import create_plan, advance_plan
    print("planning: OK")
except Exception as e:
    print(f"planning: FAIL - {e}")

try:
    from adb_agent.callbacks import enforce_plan, inject_screenshot, MAX_STEPS
    print("callbacks: OK")
except Exception as e:
    print(f"callbacks: FAIL - {e}")

try:
    from adb_agent.tools import ALL_TOOLS
    print(f"tools: {len(ALL_TOOLS)}, first={ALL_TOOLS[0].__name__}, second={ALL_TOOLS[1].__name__}")
except Exception as e:
    print(f"tools: FAIL - {e}")

try:
    from adb_agent.agent import root_agent
    has_btc = root_agent.before_tool_callback is not None
    print(f"agent: name={root_agent.name}, before_tool_callback={has_btc}")
except Exception as e:
    print(f"agent: FAIL - {e}")

print("All checks done.")
