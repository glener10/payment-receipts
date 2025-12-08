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

<DEFINICOES>
CHAVES: A "chave" ou "etiqueta" que identifica o tipo de dado (ex: "Nome do Beneficiário", "CPF", "Agência", etc). Ignore os VALORES, foque apenas nos CHAVES.
VALOR: Qualquer VALOR específico de uma Chave, você deve ignorar os valores ou tarjas pretas (usadas para anonimizar dados sensíveis) e focar apenas nas CHAVES.
</DEFINICOES>

<REGRAS_MUITO_IMPORTANTES>

- Tarjas pretas na imagem são censuras VÁLIDAS. Foque nas CHAVES e não nos VALORES.

- Se as CHAVES não forem IDÊNTICAS, não é o mesmo layout.

- Ignore os VALORES dos campos. Foque apenas nas CHAVES dos campos e suas posições. Os VALORES são diferentes entre comprovantes, mas as CHAVES permanecem as mesmas, geralmente existem uma separação visual clara entre CHAVE e VALOR, podendo ser uma quebra de linha, um espaçamento, ou um caractere especial como ":".

</REGRAS_MUITO_IMPORTANTES>

Siga estes passos estritamente:

1. Ambos layouts possuem as MESMAS CHAVES? Um layout não pode ter mais ou menos CHAVES que o outro.
2. Ambos layouts possuem as MESMAS CHAVES nos mesmos locais?
3. Ambos layouts possuem as MESMAS CHAVES na exata ordem?
4. Ambos layouts possuem presença de logotipos ou marcas d'água? Os logotipos tem o mesmo tamanho e estão na mesma posição?
5. Ambos layouts possuem os MESMOS elementos gráficos (linhas, caixas, bordas, separadores, etc)? Esses elementos estão na mesma posição, tamanho e cor? OBSERVAÇÃO IMPORTANTE: Ignore as tarjas pretas como elementos gráficos.
6. Ambos layouts estão nas mesmas dimensões (altura e largura)?

</MISSION>

<FORMATO_DE_RESPOSTA>
Após sua análise passo-a-passo, forneça o JSON final:

```json
{
    "reason": "Traga uma análise detalhada do porquê os layouts são idênticos ou diferentes. Qual diferença você encontrou entre um layout e outro. 
    IMPORTANTE: Seja detalhista em casos negativos, qual campo está diferente, qual campo está faltando, qual campo está em local diferente, etc.",
    "is_match": true/false,
    "confidence": 0.0-1.0
}
```
</FORMATO_DE_RESPOSTA>

<VALIDACAO_FINAL>
- Se na sua análise você concluiu que os layouts são semelhantes e possuem as mesmas CHAAVES só com VALOR diferentes, considere como "is_match": true pois o objetivo é comparar layouts, não valores.
</VALIDACAO_FINAL>
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
