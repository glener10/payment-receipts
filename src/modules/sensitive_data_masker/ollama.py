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
Você é um auditor rigoroso de layouts bancários.
</PERSONA>

<MISSION>
Seu objetivo é comparar a ESTRUTURA visual de dois comprovantes.
Ignore os valores (dinheiro, datas, nomes). Foque apenas nos RÓTULOS (KEYS) dos campos e suas posições.

Siga estes passos estritamente:
1. Liste os 3 primeiros rótulos (campos) visíveis no topo da Imagem 1.
2. Liste os 3 primeiros rótulos (campos) visíveis no topo da Imagem 2.
3. Verifique se a Imagem 1 possui algum campo que NÃO existe na Imagem 2 (ex: uma tem "CPF" e a outra não).
4. Compare a posição visual: Os campos estão alinhados da mesma forma?

<REGRAS>
- Tarjas pretas na imagem 1 são censuras. Ignore o conteúdo, mas verifique se o campo ainda existe.
- Se os rótulos não forem IDÊNTICOS, não é o mesmo layout.
</REGRAS>

Após sua análise passo-a-passo, forneça o JSON final:
```json
{
    "reason": "Resumo da sua análise aqui...",
    "is_match": true/false,
    "confidence": 0.0-1.0
}
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
            model="minicpm-v",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": image_paths,
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
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            os.remove(temp_template_path)
