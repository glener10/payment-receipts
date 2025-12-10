# python src/usecases/load_templates.py -n nu -e .pdf
import json
import os
import cv2

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
PDF_EXTENSION = ".pdf"


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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", required=True, help="Bank name")
    parser.add_argument("-e", "--extension", required=True, help="File extension")
    args = parser.parse_args()

    templates = load_bank_templates(args.name, args.extension)

    print(f"loaded {len(templates)} template(s) for '{args.name}':")
    for template in templates:
        print(f"  - {template['name']}{template['file_extension']}")
