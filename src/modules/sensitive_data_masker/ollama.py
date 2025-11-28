import json
import os
from pathlib import Path
import ollama

from src.utils.pdf import pdf_to_image


def compare_with_ollama(template_path, input_path):
    temp_template_path = None
    temp_input_path = None
    try:
        prompt = """
<PERSONA>
Você é um especialista em análise de documentos bancários.
</PERSONA>

<MISSION>
Analise as duas imagens fornecidas e determine se elas têm o MESMO FORMATO/LAYOUT de comprovante bancário.

ATENÇÃO! IMPORTANTE!

- Verifique se são do mesmo banco/instituição financeira
- A primeira imagem (referência) pode ter dados mascarados com tarjas pretas - IGNORE essas tarjas, foque na disposição dos elementos
- Compare apenas a ESTRUTURA, LAYOUT e FORMATO do documento, Os VALORES dos dados podem ser diferentes - isso é NORMAL.
- Foque na localização de cada elemento, as keys de cada campo devem estar no mesmo local. Por exemplo se a key "nome" de uma imagem está no canto superior esquerdo, a outra imagem também deve ter a key "nome" no canto superior esquerdo.
- Ambas imagens deve ter os mesmos elementos (keys) visíveis nas mesmas localizações/coordenadas, mesmo que os valores estejam diferentes ou mascarados.

Retorne APENAS um JSON válido (sem markdown, sem explicações extras) com:
{{
    "is_match": true/false,
    "confidence": 0.0-1.0,
    "reason": "explicação detalhada"
}}

Seja rigoroso: apenas retorne is_match=true se tiver alta confiança (>85%).
</MISSION>
"""
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
            model="qwen3-vl:8b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": image_paths,
                }
            ],
            options={"temperature": 0.1},
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
                return {
                    "is_match": False,
                    "confidence": 0.0,
                    "reason": f"Failed to parse response: {response_content[:200]}",
                }

        if not isinstance(result, dict):
            raise ValueError("Response is not a dict")

        if "is_match" not in result:
            result["is_match"] = False
        if "confidence" not in result:
            result["confidence"] = 0.0
        if "reason" not in result:
            result["reason"] = "No reason provided"

        return result
    except Exception as e:
        raise e
    finally:
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            os.remove(temp_template_path)
