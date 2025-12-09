import datetime
import argparse
import os
import json
import shutil

from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
import ollama


from src.utils.dirs import remove_empty_dirs
from src.utils.pdf import pdf_to_image

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

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

prompt = """
<PERSONA>
Você é um Auditor de Segurança da Informação (DLP) altamente cético. Sua única função é bloquear o vazamento de PII (Personally Identifiable Information).
</PERSONA>

<CONTEXTO_VISUAL>
Você está analisando comprovantes bancários Pix.
- Estrutura típica: Um RÓTULO (ex: "Destinatário") seguido de um VALOR (ex: "João da Silva").
- O usuário tentou anonimizar os VALORES aplicando tarjas pretas (retângulos sólidos).
</CONTEXTO_VISUAL>

<DEFINICAO_DE_DADO_SENSIVEL>
Considere como SENSÍVEL (Vazamento) se qualquer um destes estiver visível:
1. Nomes de Pessoas (Pessoa Física). Nota: Nomes de Bancos ou Instituições de Pagamento NÃO são sensíveis.
2. CPF ou CNPJ (parcial ou total, observe que se o CNPJ for da instituição que está enviando ou recebendo o Pix não é um dado sensível, apenas se for chave Pix).
3. Agência e Conta.
4. Chaves Pix (E-mail, Telefone, CPF).
</DEFINICAO_DE_DADO_SENSIVEL>

<REGRAS_DE_OURO>
1. **Rótulo != Valor:** O texto "CPF" ou "Nome" impresso no layout é apenas um rótulo. Isso é SEGURO. O vazamento só ocorre se o NÚMERO do CPF ou o NOME da pessoa estiver legível.
2. **A Regra da Tarja:** - Se um valor está coberto por uma tarja preta sólida: SEGURO (Ignore).
   - Se a tarja é translúcida e permite leitura: VAZAMENTO.
   - Se a tarja cobre apenas metade do nome/número: VAZAMENTO.
3. **Ignore (Safe List):**
   - Valores monetários (R$ 50,00).
   - Datas e Horários.
   - IDs de Transação (sequências longas de letras e números aleatórios).
   - Nomes de Bancos (ex: "Nubank", "Itaú", "Banco Central").
   - Mensagens de rodapé.
</REGRAS_DE_OURO>

<PROCEDIMENTO_DE_ANALISE>
Analise cada campo visualmente:
Passo 1: Identifique um campo (ex: Nome do Favorecido).
Passo 2: Olhe para o valor deste campo.
Passo 3: O valor é legível? 
    - NÃO (tem tarja preta) -> OK.
    - SIM -> É um nome de banco ou dado da Safe List?
        - SIM -> OK.
        - NÃO -> ALERTA DE VAZAMENTO.
</PROCEDIMENTO_DE_ANALISE>

<FORMATO_RESPOSTA>
Retorne apenas o JSON. Se encontrar vazamento, adicione o nome do campo em `leaked_fields`.
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

        if not isinstance(result, dict):
            return {
                "has_sensitive_data": True,
                "analysis": "Invalid response format from Ollama",
                "leaked_fields": [],
            }

        if "has_sensitive_data" not in result:
            result["has_sensitive_data"] = True
        if "analysis" not in result:
            result["analysis"] = "No analysis provided"
        if "leaked_fields" not in result:
            result["leaked_fields"] = []

        return result

    except Exception as e:
        return {
            "has_sensitive_data": True,
            "analysis": f"Error during check: {str(e)}",
            "leaked_fields": [],
        }
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

        if "has_sensitive_data" not in result:
            result["has_sensitive_data"] = True
        if "analysis" not in result:
            result["analysis"] = "No analysis provided"
        if "leaked_fields" not in result:
            result["leaked_fields"] = []

        return result

    except Exception as e:
        return {
            "has_sensitive_data": True,
            "analysis": f"Error during check: {str(e)}",
            "leaked_fields": [],
        }


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

            if result.get("has_sensitive_data", True):
                analysis = result.get("analysis", "No details provided")
                print(f"guardrails ⚠️: '{rel_path}' sensitive data found - {analysis}")
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
