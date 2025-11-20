import os
import json
import cv2
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types

load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=gemini_api_key)
gemini_client = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    generation_config=types.GenerationConfig(
        response_mime_type="application/json",
    ),
)


def compare_images_with_gemini(img1_path, img2_path, bank_name, template_name):
    """
    Use Gemini to compare if two images have the same layout/format

    Args:
        img1_path: Path to reference image (with masks)
        img2_path: Path to input image (to compare)
        bank_name: Name of the bank
        template_name: Name of the template

    Returns:
        dict: {'is_match': bool, 'confidence': float, 'reason': str}
    """
    try:
        prompt = f"""Você é um especialista em análise de documentos bancários.

Analise as duas imagens fornecidas e determine se elas têm o MESMO FORMATO/LAYOUT de comprovante bancário.

IMPORTANTE:
- A primeira imagem (referência) pode ter dados mascarados com tarjas pretas - IGNORE essas tarjas
- Compare apenas a ESTRUTURA, LAYOUT e FORMATO do documento
- Verifique se são do mesmo banco/instituição financeira
- Verifique se têm a mesma disposição de elementos (cabeçalho, campos, rodapé)
- Os VALORES dos dados podem ser diferentes (nomes, valores, datas) - isso é NORMAL
- Foque na similaridade do DESIGN e ESTRUTURA

Informações de contexto:
- Banco esperado: {bank_name}
- Template: {template_name}

Retorne um JSON com:
{{
    "is_match": true/false,
    "confidence": 0.0-1.0,
    "reason": "explicação detalhada da decisão",
    "bank_detected": "nome do banco detectado na imagem de input",
    "layout_elements": ["elemento1", "elemento2", ...] elementos de layout detectados
}}

Seja rigoroso: apenas retorne is_match=true se tiver alta confiança (>85%) de que são do mesmo formato."""

        # Read images as bytes
        with open(img1_path, "rb") as f:
            img1_data = f.read()
        with open(img2_path, "rb") as f:
            img2_data = f.read()

        # Determine mime types
        img1_ext = Path(img1_path).suffix.lower()
        img2_ext = Path(img2_path).suffix.lower()

        mime_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }

        img1_mime = mime_type_map.get(img1_ext, "image/jpeg")
        img2_mime = mime_type_map.get(img2_ext, "image/jpeg")

        # Prepare content for Gemini
        contents = [
            prompt,
            {"mime_type": img1_mime, "data": img1_data},
            {"mime_type": img2_mime, "data": img2_data},
        ]

        response = gemini_client.generate_content(contents=contents)
        result = json.loads(response.text)

        return result

    except Exception as e:
        return {
            "is_match": False,
            "confidence": 0.0,
            "reason": f"Error: {str(e)}",
            "bank_detected": "unknown",
            "layout_elements": [],
        }


def load_coordinate_templates(coordinates_dir="src/config/coordinates"):
    """
    Load all coordinate templates from the config directory

    Returns:
        dict: Dictionary with bank names as keys and list of templates as values
        Each template contains: {
            'name': str,
            'reference_image_path': str,
            'coordinates': list,
            'reference_image': numpy array
        }
    """
    templates = {}

    if not os.path.exists(coordinates_dir):
        print(f"⚠️  Coordinates directory not found: {coordinates_dir}")
        return templates

    # Iterate through each bank directory
    for bank_name in os.listdir(coordinates_dir):
        bank_dir = os.path.join(coordinates_dir, bank_name)

        if not os.path.isdir(bank_dir):
            continue

        templates[bank_name] = []

        # Find all coordinate JSON files
        json_files = [f for f in os.listdir(bank_dir) if f.endswith(".json")]

        for json_file in json_files:
            # Get the base name (e.g., coordinates_output_a)
            base_name = json_file.replace(".json", "")
            png_file = f"{base_name}.png"

            json_path = os.path.join(bank_dir, json_file)
            png_path = os.path.join(bank_dir, png_file)

            # Check if corresponding PNG exists
            if not os.path.exists(png_path):
                print(f"⚠️  Missing reference image: {png_path}")
                continue

            # Load coordinates
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    coordinates = json.load(f)

                # Load reference image
                reference_image = cv2.imread(png_path)

                if reference_image is None:
                    print(f"⚠️  Could not load reference image: {png_path}")
                    continue

                templates[bank_name].append(
                    {
                        "name": base_name,
                        "reference_image_path": png_path,
                        "coordinates": coordinates,
                        "reference_image": reference_image,
                    }
                )

            except Exception as e:
                print(f"❌ Error loading template {json_file}: {e}")
                continue

        if templates[bank_name]:
            print(
                f"📂 Loaded {len(templates[bank_name])} template(s) for '{bank_name}'"
            )

    return templates


def find_matching_template(file_path, templates, threshold=0.95):
    """
    Find the best matching template for a given file using Gemini AI

    Args:
        file_path: Path to the input file
        templates: Dictionary of templates from load_coordinate_templates
        threshold: Minimum confidence threshold (default: 0.85)

    Returns:
        dict or None: Matching template with 'bank', 'template', 'similarity' and 'reason' keys
    """
    try:
        for bank_name, bank_templates in templates.items():
            for template in bank_templates:
                result = compare_images_with_gemini(
                    template["reference_image_path"],
                    file_path,
                    bank_name,
                    template["name"],
                )

                confidence = result.get("confidence", 0.0)
                is_match = result.get("is_match", False)

                if is_match and confidence >= threshold:
                    return {
                        "bank": bank_name,
                        "template": template,
                        "similarity": confidence,
                        "is_match": is_match,
                        "reason": result.get("reason", ""),
                        "bank_detected": result.get("bank_detected", "unknown"),
                    }

        return None

    except Exception as e:
        print(f"❌ Error finding matching template: {e}")
        return None


def scale_coordinates(
    coordinates, source_width, source_height, target_width, target_height
):
    """
    Scale coordinates from source dimensions to target dimensions

    Args:
        coordinates: List of coordinate dicts with x, y, width, height
        source_width: Width of the reference image
        source_height: Height of the reference image
        target_width: Width of the target image
        target_height: Height of the target image

    Returns:
        list: Scaled coordinates
    """
    scale_x = target_width / source_width
    scale_y = target_height / source_height

    scaled_coords = []
    for coord in coordinates:
        scaled_coords.append(
            {
                "x": int(coord["x"] * scale_x),
                "y": int(coord["y"] * scale_y),
                "width": int(coord["width"] * scale_x),
                "height": int(coord["height"] * scale_y),
            }
        )

    return scaled_coords
