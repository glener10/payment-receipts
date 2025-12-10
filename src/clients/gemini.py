import json
import os
from dotenv import load_dotenv


import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pathlib import Path

from config.prompts.compare_templates_prompt import get_compare_templates_prompt
from src.utils.mime_type import get_mime_type

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

response_schema = content.Schema(
    type=content.Type.OBJECT,
    enum=[],
    required=["is_match", "confidence", "reason"],
    properties={
        "is_match": content.Schema(
            type=content.Type.BOOLEAN,
            description="True se as imagens compartilham exatamente o mesmo template/layout.",
        ),
        "confidence": content.Schema(
            type=content.Type.NUMBER, description="Grau de certeza entre 0.0 e 1.0"
        ),
        "reason": content.Schema(
            type=content.Type.STRING,
            description="Explicação técnica citando as chaves encontradas e a ordem visual.",
        ),
    },
)

generation_config = {
    "temperature": 0.0,
    "top_p": 1.0,
    "top_k": 1,
    "max_output_tokens": 2048,
    "response_mime_type": "application/json",
    "response_schema": response_schema,
}

genai.configure(api_key=gemini_api_key)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.5-flash", generation_config=generation_config
)


def compare_templates_with_gemini(template_path, input_path):
    try:
        prompt = get_compare_templates_prompt()

        with open(template_path, "rb") as f:
            template_data = f.read()
        with open(input_path, "rb") as f:
            input_data = f.read()

        template_ext = Path(template_path).suffix.lower()
        input_ext = Path(input_path).suffix.lower()

        template_mime = get_mime_type(template_ext)
        input_mime = get_mime_type(input_ext)

        contents = [
            prompt,
            {"mime_type": template_mime, "data": template_data},
            {"mime_type": input_mime, "data": input_data},
        ]

        response = gemini_client.generate_content(contents=contents)
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {"is_match": False, "confidence": 0.0, "reason": f"Error: {str(e)}"}
