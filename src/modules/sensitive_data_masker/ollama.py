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

<INPUT_FORMAT>
Você receberá EXATAMENTE 2 imagens:
- Documento A = primeira imagem
- Documento B = segunda imagem
Sempre mantenha essa ordem.
</INPUT_FORMAT>

<MISSION>
Comparar a ESTRUTURA visual de dois comprovantes: CHAVES (rótulos) e elementos gráficos fixos.
Ignore TODOS os VALORES e TARJAS pretas.
</MISSION>

<DEFINICOES>
CHAVES: rótulos/etiquetas (ex: "Nome do Beneficiário", "CPF", "Agência").  
VALOR: conteúdo do campo — IGNORAR.  
TARJA: bloco preto — IGNORAR.
</DEFINICOES>

<RULES>
- Compare CHAVES por igualdade textual EXATA (sem sinônimos).  
- Não invente CHAVES, posições ou coordenadas. Se não puder determinar posição, retorne "unknown".  
- Tarjas pretas não são elementos gráficos.  
- Considere diferença de cor quando for parte do layout (ex.: cabeçalho “Pix” verde).  
- Saída deve ser APENAS JSON conforme o FORMATO_DE_RESPOSTA.
</RULES>

<CONFIDENCE_GUIDE>
0.90–1.00: CHAVES iguais, mesma ordem, posições equivalentes.  
0.70–0.89: CHAVES iguais, pequenas variações ≤5%.  
0.40–0.69: CHAVES iguais, ordem diferente ou deslocamentos 5–15%.  
0.00–0.39: CHAVES diferentes ou OCR falho.
</CONFIDENCE_GUIDE>

<FORMATO_DE_RESPOSTA>
Retorne somente JSON válido:

{
  "reason": "<análise detalhada passo-a-passo>",
  "is_match": true|false,
  "confidence": 0.0-1.0
}
</FORMATO_DE_RESPOSTA>
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
            model="qwen2.5vl:7b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": image_paths,
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
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            os.remove(temp_template_path)
