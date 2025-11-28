import os

import cv2

from src.modules.sensitive_data_masker.matcher import find_best_template
from src.modules.sensitive_data_masker.coordinates import scale_coordinates
from src.modules.sensitive_data_masker.masking import (
    apply_mask_to_image,
    apply_mask_to_pdf,
)


async def process_files_with_coordinate_matching(
    input_path: str, output_dir: str, use_ollama: bool = False
):
    for root, _, files in os.walk(input_path):
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
            process_file(file_path, input_path, output_dir, use_ollama)


def process_file(file_path, base_input_path, output_dir, use_ollama=False):
    person_name, bank_name = extract_path_info(file_path, base_input_path)

    if not person_name or not bank_name:
        print(f"sensitive_data_masker: invalid path structure: '{file_path}' ⚠️")
        return

    try:
        model_name = "Ollama (local)" if use_ollama else "Gemini"
        print(
            f"sensitive_data_masker: '{file_path}' [{bank_name}] processing with {model_name}..."
        )
        match = find_best_template(file_path, bank_name, use_ollama=use_ollama)

        if not match:
            print(
                f"sensitive_data_masker: '{file_path}' [{bank_name}] no match found ⚠️"
            )
            return

        template = match["template"]
        coordinates = template["coordinates"]

        _, ext = os.path.splitext(file_path)
        ext_lower = ext.lower()

        if ext_lower == ".pdf":
            import fitz

            doc = fitz.open(file_path)
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            import numpy as np

            img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            if pix.n == 4:
                input_image = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
            else:
                input_image = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)
            doc.close()
        else:
            input_image = cv2.imread(file_path)

        if input_image is None:
            print(
                f"sensitive_data_masker: '{file_path}' [{bank_name}] could not load file ⚠️"
            )
            return

        input_height, input_width = input_image.shape[:2]

        if template["reference_image"] is not None:
            ref_image = template["reference_image"]
            ref_height, ref_width = ref_image.shape[:2]
        else:
            ref_height, ref_width = input_height, input_width

        if input_width != ref_width or input_height != ref_height:
            coordinates = scale_coordinates(
                coordinates, ref_width, ref_height, input_width, input_height
            )

        rel_path = os.path.relpath(file_path, base_input_path)
        output_path = os.path.join(output_dir, rel_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        _, ext = os.path.splitext(file_path)
        ext_lower = ext.lower()

        success = False
        if ext_lower in [".jpg", ".jpeg", ".png"]:
            success = apply_mask_to_image(file_path, coordinates, output_path)
        elif ext_lower == ".pdf":
            success = apply_mask_to_pdf(file_path, coordinates, output_path)

        if success:
            print(
                f"sensitive_data_masker: '{file_path}' [{bank_name}] masked with template [{template['bank_name']}/{template['name']}.{template['file_extension']}], confidence: {match['confidence']:.2f}, reason: {match['reason']} ✅"
            )
            return
        else:
            print(
                f"sensitive_data_masker: '{file_path}' [{bank_name}] masked failed ❌"
            )
            return

    except Exception as e:
        print(f"sensitive_data_masker: error processing '{file_path}': {e}")
        return


def extract_path_info(file_path, base_path):
    rel_path = os.path.relpath(file_path, base_path)
    parts = rel_path.split(os.sep)

    if len(parts) < 2:
        return None, None

    if len(parts) == 2:
        bank_name = parts[0]
        person_name = "unknown"
    else:
        person_name = parts[0]
        bank_name = parts[1]

    return person_name, bank_name
