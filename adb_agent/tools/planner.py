"""Planning tools for the agent loop."""

import json
import os

from google import genai
from google.genai import types
from google.adk.tools import ToolContext


PLANNING_PROMPT = """You are a phone automation planning assistant. Decompose the following task into clear ordered steps for an Android automation agent.

Rules:
- 1–5 steps maximum

Task: {task}"""


def create_plan(task: str, tool_context: ToolContext) -> dict:
    """Call the LLM to generate a structured execution plan and save it to the session state.

    You must call this tool first before taking any actions on the device.

    Args:
        task: The user's requested task to automate.
        tool_context: ADK ToolContext — provides session state access.
    Returns:
        dict with the generated plan details.
    """
    use_local_llm = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
    model_name = os.getenv("MODEL_NAME", "gemini-3-flash-preview")
    
    if use_local_llm:
        # Use litellm for OpenAI-compatible endpoints (like vLLM)
        from litellm import completion
        vllm_base_url = os.getenv("VLLM_BASE_URL")
        
        response_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "plan_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string", "description": "Concise restatement of the task"},
                        "steps": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of action steps (1-5 maximum)"
                        }
                    },
                    "required": ["goal", "steps"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }
        
        response = completion(
            model=f"openai/{model_name}",
            messages=[{"role": "user", "content": PLANNING_PROMPT.format(task=task)}],
            api_base=vllm_base_url,
            api_key="dummy",
            temperature=0.1,
            response_format=response_schema
        )
        response_text = response.choices[0].message.content
    else:
        client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY", "dummy"))
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "goal": {"type": "STRING", "description": "Concise restatement of the task"},
                "steps": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of action steps (1-5 maximum)"
                }
            },
            "required": ["goal", "steps"]
        }

        response = client.models.generate_content(
            model=model_name,
            contents=PLANNING_PROMPT.format(task=task),
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )
        response_text = response.text

    data = json.loads(response_text)
    plan = {
        "goal": data["goal"],
        "steps": data["steps"],
        "current_step": 0,
        "completed_observations": [],
    }
    
    tool_context.state["plan"] = plan
    
    return {
        "status": "success",
        "message": "Plan created successfully.",
        "plan": plan
    }


def update_plan(observation: str, tool_context: ToolContext) -> dict:
    """Mark the current plan step as done and advance to the next step.

    Call this when you visually confirm the current step is completed.

    Args:
        observation: Brief description of what you see that confirms the step is done.
        tool_context: ADK ToolContext — provides session state access.
    Returns:
        dict with next step info, or signal that all steps are complete.
    """
    plan = tool_context.state.get("plan")
    if plan is None:
        return {"status": "error", "error_message": "No plan exists. Call create_plan first."}
    if plan["current_step"] >= len(plan["steps"]):
        return {"status": "error", "error_message": "All steps already complete."}

    plan["completed_observations"].append(observation)
    plan["current_step"] += 1
    tool_context.state["plan"] = plan  # write back to session state

    if plan["current_step"] >= len(plan["steps"]):
        return {
            "status": "all_steps_complete",
            "message": "All plan steps completed. Task will terminate automatically.",
        }

    i = plan["current_step"]
    return {
        "status": "success",
        "message": f"Advanced to step {i + 1}/{len(plan['steps'])}",
        "current_action": plan["steps"][i],
    }
