import json
import os
from dotenv import load_dotenv


import google.generativeai as genai
from google.generativeai import types
from pathlib import Path

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_api_key)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=types.GenerationConfig(
        response_mime_type="application/json",
    ),
)


def compare_with_gemini(template_path, input_path):
    try:
        prompt = """
<PERSONA>
Você é um especialista em análise de documentos bancários.
</PERSONA>

<MISSION>
Analise as duas imagens fornecidas e determine se elas têm o MESMO FORMATO/LAYOUT de comprovante bancário.

ATENÇÃO! IMPORTANTE!

- Por mais que os comprovantes são do mesmo banco, eles podem ter dados diferentes, keys para mais, por exemplo um mostrar o "CPF" e outro não. Nesse caso você deve retornar is_match=false, pois os elementos visíveis não são os mesmos.
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

        with open(template_path, "rb") as f:
            template_data = f.read()
        with open(input_path, "rb") as f:
            input_data = f.read()

        template_ext = Path(template_path).suffix.lower()
        input_ext = Path(input_path).suffix.lower()

        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".pdf": "application/pdf",
        }

        template_mime = mime_map.get(template_ext, "image/jpeg")
        input_mime = mime_map.get(input_ext, "image/jpeg")

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
