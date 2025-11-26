import json
import base64
import requests


def compare_with_deepseek(template_path, input_path, bank_name, template_name):
    try:
        prompt = f"""Você é um especialista em análise de documentos bancários.

Analise as duas imagens fornecidas e determine se elas têm o MESMO FORMATO/LAYOUT de comprovante bancário.

IMPORTANTE:
- A primeira imagem (referência) pode ter dados mascarados com tarjas pretas - IGNORE essas tarjas
- Compare apenas a ESTRUTURA, LAYOUT e FORMATO do documento
- Verifique se são do mesmo banco/instituição financeira
- Os VALORES dos dados podem ser diferentes - isso é NORMAL
- Foque na similaridade do DESIGN e ESTRUTURA

Banco esperado: {bank_name}
Template: {template_name}

Retorne APENAS um JSON válido (sem markdown, sem explicações extras) com:
{{
    "is_match": true/false,
    "confidence": 0.0-1.0,
    "reason": "explicação detalhada"
}}

Seja rigoroso: apenas retorne is_match=true se tiver alta confiança (>85%)."""

        with open(template_path, "rb") as f:
            template_b64 = base64.b64encode(f.read()).decode("utf-8")

        with open(input_path, "rb") as f:
            input_b64 = base64.b64encode(f.read()).decode("utf-8")

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-r1:1.5b",
                "prompt": prompt,
                "images": [template_b64, input_b64],
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )

        if response.status_code != 200:
            return {
                "is_match": False,
                "confidence": 0.0,
                "reason": f"Ollama API error: {response.status_code}",
            }

        response_data = response.json()
        response_text = response_data.get("response", "{}")

        try:
            result = json.loads(response_text)

            if not isinstance(result, dict):
                raise ValueError("Response is not a dict")

            if "is_match" not in result:
                result["is_match"] = False
            if "confidence" not in result:
                result["confidence"] = 0.0
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
                "is_match": False,
                "confidence": 0.0,
                "reason": f"Failed to parse response: {response_text[:200]}",
            }

    except requests.exceptions.ConnectionError:
        return {
            "is_match": False,
            "confidence": 0.0,
            "reason": "Cannot connect to Ollama. Is it running? (ollama serve)",
        }
    except requests.exceptions.Timeout:
        return {
            "is_match": False,
            "confidence": 0.0,
            "reason": "Ollama request timeout (>120s)",
        }
    except Exception as e:
        return {"is_match": False, "confidence": 0.0, "reason": f"Error: {str(e)}"}
