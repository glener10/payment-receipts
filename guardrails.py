import datetime
import argparse
import os
import json
import shutil
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types

from src.utils.dirs import remove_empty_dirs

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_api_key)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=types.GenerationConfig(
        response_mime_type="application/json",
    ),
)

prompt = """Analise esta imagem de comprovante bancário e verifique se há DADOS SENSÍVEIS VISÍVEIS.

Dados sensíveis incluem:
- Nome completo de pessoas
- CPF
- Chave Pix (CPF, email, telefone, chave aleatória)
- Número de conta bancária
- Agência
- Identificador da transação

Retorne APENAS um JSON válido (sem markdown, sem explicações extras) com:
{
    "has_sensitive_data": true/false,
    "reason": "explicação do que foi encontrado ou confirmação de que tudo está mascarado"
}

Se TODOS os dados sensíveis estiverem cobertos por tarjas pretas, retorne has_sensitive_data=false.
Se QUALQUER dado sensível estiver visível, retorne has_sensitive_data=true."""


def check_sensitive_data_deepseek(file_path):
    """
    Check if file contains visible sensitive data using DeepSeek (Ollama)

    Returns:
        dict: {'has_sensitive_data': bool, 'reason': str}
    """
    try:
        with open(file_path, "rb") as f:
            file_b64 = base64.b64encode(f.read()).decode("utf-8")

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:7b",
                "prompt": prompt,
                "images": [file_b64],
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )

        if response.status_code != 200:
            return {
                "has_sensitive_data": True,
                "reason": f"Ollama API error: {response.status_code}",
            }

        response_data = response.json()
        response_text = response_data.get("response", "{}")

        try:
            result = json.loads(response_text)

            if not isinstance(result, dict):
                raise ValueError("Response is not a dict")

            if "has_sensitive_data" not in result:
                result["has_sensitive_data"] = True
            if "reason" not in result:
                result["reason"] = "No reason provided"

            return result

        except json.JSONDecodeError:
            import re

            json_match = re.search(
                r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL
            )
            if json_match:
                result = json.loads(json_match.group(1))
                return result

            return {
                "has_sensitive_data": True,
                "reason": f"Failed to parse response: {response_text[:200]}",
            }
    except Exception as e:
        return {
            "has_sensitive_data": True,
            "reason": f"Error during check: {str(e)}",
        }


def check_sensitive_data(file_path):
    """
    Check if file contains visible sensitive data using Gemini

    Returns:
        dict: {'has_sensitive_data': bool, 'reason': str}
    """
    try:
        with open(file_path, "rb") as f:
            file_data = f.read()

        file_ext = Path(file_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }
        mime_type = mime_map.get(file_ext, "image/jpeg")

        contents = [prompt, {"mime_type": mime_type, "data": file_data}]

        response = gemini_client.generate_content(contents=contents)
        result = json.loads(response.text)
        return result

    except Exception as e:
        return {
            "has_sensitive_data": True,
            "reason": f"Error during check: {str(e)}",
        }


def process_files(input_dir, output_dir, use_deepseek=False):
    """
    Process all files in input directory and validate masking

    Args:
        input_dir: Directory with masked files to validate
        output_dir: Directory to copy files that passed validation
        use_deepseek: Use DeepSeek (local) instead of Gemini

    Returns:
        dict: Statistics about the validation
    """
    check_function = (
        check_sensitive_data_deepseek if use_deepseek else check_sensitive_data
    )

    for root, _, files in os.walk(input_dir):
        for file in files:
            _, ext = os.path.splitext(file)
            if ext.lower() not in [
                ".png",
                ".jpg",
                ".jpeg",
                ".pdf",
            ]:
                continue

            file_path = os.path.join(root, file)

            rel_path = os.path.relpath(file_path, input_dir)

            print(f"guardrails: validating '{rel_path}' 🔍")
            result = check_function(file_path)

            if result["has_sensitive_data"]:
                print(
                    f"guardrails: '{rel_path}' sensitive data found - {result['reason']} ⚠️"
                )
            else:
                output_file_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                shutil.move(file_path, output_file_path)
                print(
                    f"guardrails: '{rel_path}' all data masked - {result['reason']} ✅"
                )


def main():
    parser = argparse.ArgumentParser(
        description="Validate masked files for sensitive data"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Directory containing masked files to validate",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Directory to copy files that passed validation",
    )
    parser.add_argument(
        "--deepseek",
        action="store_true",
        help="Use local DeepSeek model via Ollama instead of Gemini (better privacy)",
    )

    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)

    if not os.path.exists(input_dir):
        print(f"guardrails: ❌ Input directory does not exist: {input_dir}")
        return

    if args.deepseek:
        print("guardrails: Using DeepSeek (local) for validation 🔒")
    else:
        print("guardrails: Using Gemini for validation ☁️")

    os.makedirs(output_dir, exist_ok=True)

    process_files(input_dir, output_dir, args.deepseek)
    remove_empty_dirs(input_dir)


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"guardrails: 🚀 Starting guardrails validation at {start_time}")

    main()

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    print(f"guardrails: ✅  Execution finished. Total time: {total_time}")
