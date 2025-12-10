import json
import os
from dotenv import load_dotenv

from google.generativeai import types
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pathlib import Path

from src.config.prompts.identify_bank_of_payment_receipt_prompt import (
    get_identify_bank_of_payment_receipt_prompt,
)
from src.config.prompts.compare_templates_prompt import get_compare_templates_prompt
from src.config.prompts.guardrails_prompt import get_guardrails_prompt
from src.utils.mime_type import get_mime_type

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")


def compare_templates_with_gemini(template_path, input_path):
    try:
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
                    type=content.Type.NUMBER,
                    description="Grau de certeza entre 0.0 e 1.0",
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


def check_sensitive_data_with_gemini(file_path):
    print("guardrails ☁️: Using Gemini for validation")
    try:
        response_schema = content.Schema(
            type=content.Type.OBJECT,
            enum=[],
            required=["analysis", "has_sensitive_data", "leaked_fields"],
            properties={
                "analysis": content.Schema(
                    type=content.Type.STRING,
                    description="Explicação passo a passo. Se houver vazamento, descreva onde e o que foi lido.",
                ),
                "has_sensitive_data": content.Schema(
                    type=content.Type.BOOLEAN,
                    description="TRUE se houver qualquer PII (nome, cpf, conta) legível. FALSE se tudo estiver censurado/mascarado.",
                ),
                "leaked_fields": content.Schema(
                    type=content.Type.ARRAY,
                    description="Lista dos tipos de dados que vazaram (ex: ['NOME_DO_PAGADOR', 'CPF_DESTINATARIO']). Retorne lista vazia [] se tudo estiver seguro.",
                    items=content.Schema(type=content.Type.STRING),
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
        with open(file_path, "rb") as f:
            file_data = f.read()

        file_ext = Path(file_path).suffix.lower()
        mime_type = get_mime_type(file_ext)

        contents = [
            get_guardrails_prompt(),
            {"mime_type": mime_type, "data": file_data},
        ]

        response = gemini_client.generate_content(contents=contents)

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError:
            import re

            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", response.text, re.DOTALL
            )
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                return {
                    "has_sensitive_data": True,
                    "analysis": f"Failed to parse Gemini response: {response.text[:200]}",
                    "leaked_fields": [],
                }

        if not isinstance(result, dict):
            return {
                "has_sensitive_data": True,
                "analysis": "Invalid response format from Gemini",
                "leaked_fields": [],
            }
        return result

    except Exception as e:
        return {
            "has_sensitive_data": True,
            "analysis": f"Error during check: {str(e)}",
            "leaked_fields": [],
        }


def get_bank_of_payment_receipt(file_path: str) -> str:
    try:
        contents = [get_identify_bank_of_payment_receipt_prompt()]
        with open(file_path, "rb") as f:
            file_data = f.read()

        file_ext = Path(file_path).suffix.lower()
        mime_type = get_mime_type(file_ext)
        contents.append({"mime_type": mime_type, "data": file_data})

        genai.configure(api_key=gemini_api_key)
        gemini_client = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=types.GenerationConfig(
                response_mime_type="text/plain",
            ),
        )
        response = gemini_client.generate_content(contents=contents)

        return {"classify": response.text, "path": file_path}
    except Exception as e:
        print(f"get_bank_of_receipt - error in {file_path}: {e}")
        return {"classify": None, "path": file_path}
