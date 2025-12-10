import json
import os
from pathlib import Path
import ollama

from config.prompts.compare_templates_prompt_ollama import (
    get_compare_templates_prompt_ollama,
)
from src.utils.pdf import pdf_to_image


def compare_templates_with_ollama(template_path, input_path):
    temp_template_path = None
    temp_input_path = None
    try:
        prompt = get_compare_templates_prompt_ollama()
        file_ext = Path(template_path).suffix.lower()

        if file_ext == ".pdf":
            temp_template_path = pdf_to_image(template_path)
            temp_input_path = pdf_to_image(input_path)

        image_paths = (
            [temp_template_path, temp_input_path]
            if temp_template_path and temp_input_path
            else [template_path, input_path]
        )

        response = ollama.chat(
            model="qwen2.5vl:7b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": image_paths,
                }
            ],
            options={"temperature": 0.0},
            format="json",
        )

        response_content = response["message"]["content"]

        try:
            result = json.loads(response_content)
        except json.JSONDecodeError:
            import re

            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", response_content, re.DOTALL
            )
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                raise ValueError("No valid JSON found in response")

        return result
    except Exception as e:
        raise e
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            os.remove(temp_template_path)
