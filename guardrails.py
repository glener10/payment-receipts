import datetime
import argparse
import os
import json
import shutil

from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types
import ollama


from src.utils.dirs import remove_empty_dirs
from src.utils.pdf import pdf_to_image

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_api_key)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=types.GenerationConfig(
        response_mime_type="application/json",
    ),
)

prompt = """
<PERSONA>
Você é um Auditor de Privacidade (DLP - Data Loss Prevention) especializado em verificar redação/anonimização em documentos.
</PERSONA>

<DEFINICOES>
DADO SENSÍVEL: Qualquer VALOR específico que identifique uma pessoa ou conta.
RÓTULO: O nome do campo (ex: as palavras "CPF", "Agência", "Nome", "Valor"). Rótulos NÃO são sensíveis.
ANONIMIZADO: Quando o valor está coberto por uma tarja preta sólida, tornando impossível a leitura.
</DEFINICOES>

<MISSAO>
Examine a imagem e verifique se algum VALOR SENSÍVEL "escapou" da anonimização.
Você deve ignorar os RÓTULOS. Foque apenas no conteúdo/valor ao lado ou abaixo do rótulo.

Verifique especificamente os VALORES de:
1. Nomes de pessoas (Beneficiário ou Pagador).
2. Números de CPF ou CNPJ.
3. Chaves Pix.
4. Números de Agência e Conta.

<REGRAS DE DECISÃO>
- Se você consegue ler qualquer parte de um número de CPF, Conta ou Nome -> has_sensitive_data = true.
- Se você vê apenas tarjas pretas onde deveriam estar os dados -> has_sensitive_data = false.
- Se você vê a palavra "CPF" mas o número ao lado está coberto -> has_sensitive_data = false.
- Vazamento Parcial: Se uma tarja cobre apenas metade de um nome ou número, considere como DADO SENSÍVEL VISÍVEL.

Responda estritamente neste formato JSON:
{
    "analysis": "Descreva brevemente o que você vê nos campos de Nome, CPF e Conta (se estão legíveis ou tarjados)",
    "has_sensitive_data": true/false
}
</MISSAO>
"""


def check_sensitive_data_ollama(file_path):
    temp_image = None
    try:
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".pdf":
            temp_image = pdf_to_image(file_path)
            file_path = temp_image

        response = ollama.chat(
            model="minicpm-v",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [file_path],
                }
            ],
            options={"temperature": 0.0, "num_ctx": 4096},
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
        if temp_image and os.path.exists(temp_image):
            os.remove(temp_image)


def check_sensitive_data(file_path):
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
        raise e


def process_files(input_dir, output_dir, use_ollama=False):
    check_function = check_sensitive_data_ollama if use_ollama else check_sensitive_data

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

            print(f"guardrails 🔍: validating '{rel_path}'")
            result = check_function(file_path)

            if result["has_sensitive_data"]:
                print(
                    f"guardrails ⚠️: '{rel_path}' sensitive data found - {result['analysis']}"
                )
            else:
                output_file_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                shutil.move(file_path, output_file_path)
                print(
                    f"guardrails ✅: '{rel_path}' all data masked - {result['analysis']}"
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
        "--ollama",
        action="store_true",
        help="use local model via Ollama instead of Gemini (better privacy)",
    )

    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)

    if not os.path.exists(input_dir):
        print(f"guardrails ❌:  Input directory does not exist: {input_dir}")
        return

    if args.ollama:
        print("guardrails 🔒: Using ollama (local) for validation")
    else:
        print("guardrails ☁️: Using Gemini for validation")

    os.makedirs(output_dir, exist_ok=True)

    process_files(input_dir, output_dir, args.ollama)
    remove_empty_dirs(input_dir)


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"guardrails 🚀: Starting guardrails validation at {start_time}")

    main()

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    print(f"guardrails ✅: Execution finished. Total time: {total_time}")
