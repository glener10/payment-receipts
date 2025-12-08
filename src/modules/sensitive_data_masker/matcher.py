import os
import json
import cv2

from src.modules.sensitive_data_masker.gemini import compare_with_gemini
from src.modules.sensitive_data_masker.ollama import compare_with_ollama

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSION = ".pdf"


def find_best_template(input_path, bank_name, use_ollama=False):
    _, file_ext = os.path.splitext(input_path)
    templates = load_bank_templates(bank_name, file_ext)

    if not templates:
        return None

    response = None
    best_confidence = 0.0

    compare_function = compare_with_ollama if use_ollama else compare_with_gemini

    for template in templates:
        result = compare_function(template["reference_path"], input_path)

        confidence = result.get("confidence", 0.0)
        is_match = result.get("is_match", False)

        if not response or (confidence > best_confidence):
            best_confidence = confidence
            response = {
                "template": template,
                "confidence": confidence,
                "reason": result.get("reason", ""),
                "is_match": is_match,
            }

    if response:
        return response

    return None


def load_bank_templates(
    bank_name, file_extension, coordinates_dir="src/config/coordinates"
):
    templates = []
    bank_dir = os.path.join(coordinates_dir, bank_name)

    if not os.path.exists(bank_dir):
        raise FileNotFoundError(
            f"sensitive_data_masker ⚠️: bank directory not found: {bank_dir}"
        )

    is_pdf = file_extension.lower() == PDF_EXTENSION
    valid_extensions = {PDF_EXTENSION} if is_pdf else IMAGE_EXTENSIONS

    json_files = [f for f in os.listdir(bank_dir) if f.endswith(".json")]

    for json_file in json_files:
        base_name = json_file.replace(".json", "")
        json_path = os.path.join(bank_dir, json_file)

        ref_path = None
        for ext in valid_extensions:
            potential_ref = os.path.join(bank_dir, f"{base_name}{ext}")
            if os.path.exists(potential_ref):
                ref_path = potential_ref
                break

        if not ref_path:
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                coordinates = json.load(f)

            if ref_path.lower().endswith(".pdf"):
                reference_image = None
            else:
                reference_image = cv2.imread(ref_path)
                if reference_image is None:
                    continue

            templates.append(
                {
                    "name": base_name,
                    "reference_path": ref_path,
                    "coordinates": coordinates,
                    "reference_image": reference_image,
                    "bank_name": bank_name,
                    "file_extension": file_extension,
                }
            )
        except Exception as e:
            print(f"sensitive_data_masker ❌: error loading template {json_file}: {e}")
            continue
    return templates
