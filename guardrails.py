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
Você é um Auditor de Privacidade (DLP - Data Loss Prevention) especializado em verificar se valores sensíveis foram corretamente anonimizados em comprovantes bancários.
</PERSONA>

<DEFINICOES>
DADO_SENSIVEL: Qualquer VALOR que identifique uma pessoa ou conta, incluindo:
- Nome de pessoa
- CPF ou CNPJ
- Chave Pix (qualquer tipo)
- Agência e Conta bancária

ROTULO: A etiqueta/chave usada pelo layout (ex: “Nome do Beneficiário”, “CPF”). 
Você deve IGNORAR todos os rótulos.
</DEFINICOES>

<MISSAO>
Analise a imagem e verifique se ALGUM DADO_SENSIVEL aparece legível.

Regras de interpretação:
- Foque apenas nos VALORES, nunca nos rótulos.
- Se um valor deveria estar anonimizando e está coberto por TARJA PRETA sólida → considere MASACARADO.
- Se apenas parte do valor estiver visível (mesmo 1 caractere) → has_sensitive_data = true.
- Ignore preços, datas, horários, códigos de transação, identificadores internos, hashes, valores monetários e qualquer número que claramente não seja um dado sensível.
- Considere que o comprovante pode estar em português ou inglês.
</MISSAO>

<CONDICAO_CRITICA>
Se PELO MENOS UM DADO_SENSIVEL estiver parcialmente legível → retorne has_sensitive_data = true.
Se TODOS os DADOS_SENSIVEIS estiverem totalmente cobertos por tarjas pretas → retorne has_sensitive_data = false.
</CONDICAO_CRITICA>

<FORMATO_DE_RESPOSTA>
Responda estritamente no seguinte JSON:
{
    "analysis": "Descrição completa da sua análise, em casos negativos cite quais chaves e valores sensíveis apareceram legíveis.",
    "has_sensitive_data": true/false
}
</FORMATO_DE_RESPOSTA>

"""


def check_sensitive_data_ollama(file_path):
    temp_image = None
    try:
        file_ext = Path(file_path).suffix.lower()
        if file_ext == ".pdf":
            temp_image = pdf_to_image(file_path)
            file_path = temp_image

        response = ollama.chat(
            model="qwen2.5vl:7b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [file_path],
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
