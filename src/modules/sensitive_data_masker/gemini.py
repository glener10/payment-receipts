import json
import os
from dotenv import load_dotenv


import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from pathlib import Path

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

response_schema = content.Schema(
    type=content.Type.OBJECT,
    enum=[],
    required=["is_match", "confidence", "reason"],
    properties={
        "is_match": content.Schema(
            type=content.Type.BOOLEAN,
            description="True se as imagens compartilham exatamente o mesmo template/layout.",
        ),
        "confidence": content.Schema(
            type=content.Type.NUMBER, description="Grau de certeza entre 0.0 e 1.0"
        ),
        "reason": content.Schema(
            type=content.Type.STRING,
            description="Explicação técnica citando as chaves encontradas e a ordem visual.",
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


def compare_with_gemini(template_path, input_path):
    try:
        prompt = """
<PERSONA>
Você é um Analista Forense de Documentos Bancários especializado em detecção de fraude e verificação de templates.
</PERSONA>

<CONTEXTO>
O objetivo é verificar se dois comprovantes de Pix pertencem ao mesmo "Layout Mestre" (mesmo banco, mesma versão de app).
Você receberá duas imagens. Uma delas pode conter tarjas pretas (censura de dados sensíveis).
</CONTEXTO>

<INSTRUCOES_DE_VISAO>
1.  **Ignore as Tarjas:** Trate tarjas pretas/coloridas cobrindo valores como "ruído irrelevante". O layout existe *através* delas.
2.  **Foco nas Chaves (Keys):** Identifique os rótulos dos campos (ex: "Destinatário", "Valor", "Data", "ID da transação").
3.  **Foco na Identidade Visual:** Logotipo do banco, cor de fundo do cabeçalho, fontes utilizadas.
</INSTRUCOES_DE_VISAO>

<ALGORITMO_DE_COMPARACAO>
Execute mentalmente estes passos:
1.  Identifique a instituição financeira de ambas as imagens. Se forem diferentes -> `is_match: false`.
2.  Extraia a lista ordenada de CHAVES (Labels) da Imagem A (de cima para baixo).
3.  Extraia a lista ordenada de CHAVES (Labels) da Imagem B (de cima para baixo).
4.  Compare as duas listas. Elas devem ser idênticas em conteúdo e ordem.
    * *Permissão:* Aceite pequenas variações de OCR ou corte de imagem (ex: rodapé cortado), desde que o "corpo" do comprovante seja igual.
    * *Proibição:* Se a Imagem A tem os campos alinhados à esquerda e a Imagem B centralizados, isso é uma quebra de estrutura.
</ALGORITMO_DE_COMPARACAO>

<CRITERIOS_DE_CONFIANCA>
- 1.0: Mesmo banco, logos idênticos, mesma lista de chaves na exata mesma ordem visual.
- 0.8: Mesmo banco e estrutura, mas uma imagem tem qualidade inferior ou corte leve que dificulta leitura de 1 ou 2 chaves.
- 0.2: Mesmo banco, mas layout diferente (ex: comprovante web vs comprovante mobile).
- 0.0: Bancos diferentes ou documentos não relacionados.
</CRITERIOS_DE_CONFIANCA>

<FORMATO_DE_RESPOSTA>
Responda APENAS com o JSON. Não inclua markdown (```json).
Certifique-se de preencher o campo "reason" com a evidência: liste as chaves encontradas em ambos para justificar.
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
