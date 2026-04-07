import pytest
import os
import json
import io
from dotenv import load_dotenv
from PIL import Image, ImageDraw

from google.adk.models.lite_llm import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from adb_agent.tools.screen import take_screenshot, resize_screenshot

@pytest.mark.asyncio
async def test_llm_annotation():
    load_dotenv()
    
    model_name = os.getenv("MODEL_NAME", "gemma-4-31b-it")
    vllm_base_url = os.getenv("VLLM_BASE_URL")
    
    if not vllm_base_url:
        pytest.skip("VLLM_BASE_URL not set, skipping local LLM test")
        
    model = LiteLlm(model=f"openai/{model_name}", api_base=vllm_base_url, api_key="dummy", drop_params=True, tool_choice="none")
    
    # 1. Take screenshot
    try:
        raw_png = take_screenshot()
    except Exception as e:
        pytest.skip(f"ADB not connected or failed: {e}")
        
    # Resize for LLM
    jpg_bytes = resize_screenshot(raw_png, max_size=1024)
    
    # 2. Ask LLM to annotate
    prompt = """
    Please analyze this mobile screenshot and identify all interactive UI elements (buttons, text fields, icons, etc.).
    Return a JSON array of objects, where each object has:
    - "label": A short description of the element
    - "bbox": [ymin, xmin, ymax, xmax] coordinates normalized between 0.0 and 1000.0
    
    Only return valid JSON. Do not include markdown formatting or other text.
    """
    
    req = LlmRequest(
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=jpg_bytes, mime_type="image/jpeg"),
                    types.Part.from_text(text=prompt)
                ]
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    
    response_text = ""
    async for resp in model.generate_content_async(req):
        if resp.content and resp.content.parts:
            for part in resp.content.parts:
                if part.text:
                    response_text += part.text
                    
    assert response_text, "LLM returned empty response"
    
    # Parse JSON
    try:
        # Sometimes models wrap in ```json ... ```
        if "```json" in response_text:
            json_str = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            json_str = response_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = response_text.strip()
            
        elements = json.loads(json_str)
    except Exception as e:
        pytest.fail(f"Failed to parse LLM response as JSON: {e}\nResponse: {response_text}")
        
    assert isinstance(elements, list), "Expected a list of elements"
    
    # 3. Draw bounding boxes and save
    img = Image.open(io.BytesIO(jpg_bytes))
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    for el in elements:
        if "bbox" in el and len(el["bbox"]) == 4:
            ymin, xmin, ymax, xmax = el["bbox"]
            # Convert normalized 0-1000 coordinates to actual pixels
            y1 = (ymin / 1000.0) * height
            x1 = (xmin / 1000.0) * width
            y2 = (ymax / 1000.0) * height
            x2 = (xmax / 1000.0) * width
            
            draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
            if "label" in el:
                draw.text((x1, y1 - 10), el["label"], fill="red")
                
    output_path = "annotated_screenshot.jpg"
    img.save(output_path)
    assert os.path.exists(output_path)
