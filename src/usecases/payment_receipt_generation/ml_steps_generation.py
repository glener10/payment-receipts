# python src/usecases/payment_receipt_generation/ml_steps_generation.py -i 'dataset_just_banks_and_random_name/nu/0ercxg1eypyb_1766015257435.jpeg'
import os
import sys
import cv2
import json
import pytesseract

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    )

from src.clients.gemini import generate_payment_receipt_with_json_instructions


def identify_region_type_from_left(image, x, y, w, h, debug_folder, region_index=0):
    if min(x, 350) < 10 or (x - 5) <= 0 or (y + h) <= y:
        return ""

    left_roi = image[y : y + h, 0 : x - 5]
    if left_roi.size == 0:
        return ""

    os.makedirs(debug_folder, exist_ok=True)
    cv2.imwrite(os.path.join(debug_folder, f"roi_left_{region_index}.jpg"), left_roi)

    try:
        gray = cv2.cvtColor(left_roi, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        configs = ["--psm 6", "--psm 7", "--psm 11"]
        texts = [
            (cfg, pytesseract.image_to_string(thresh, config=cfg, lang="por").strip())
            for cfg in configs
        ]
        non_empty = [(cfg, t) for cfg, t in texts if t and len(t) <= 50]

        if not non_empty:
            return ""

        from collections import Counter

        text_list = [t for _, t in non_empty]

        if len(text_list) >= 3:
            most_common = Counter(text_list).most_common(1)[0]
            extracted = (
                most_common[0]
                if most_common[1] >= 2
                else min(non_empty, key=lambda x: len(x[1]))[1]
            )
        else:
            extracted = min(non_empty, key=lambda x: len(x[1]))[1]

        cv2.imwrite(os.path.join(debug_folder, f"roi_{region_index}_otsu.jpg"), thresh)
        cv2.imwrite(
            os.path.join(debug_folder, f"roi_{region_index}_resized.jpg"), resized
        )
        with open(
            os.path.join(debug_folder, f"roi_left_{region_index}_text.txt"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(f"Selected: {extracted}\n\n")
            for cfg, t in texts:
                f.write(f"{cfg}:\n{t}\n\n")

        return extracted.strip()
    except Exception:
        return ""


def detect_masked_regions(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_regions = []
    debug_image = image.copy()

    for i, cnt in enumerate(contours):
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 30 and h > 15:
            detected_regions.append({"x": x, "y": y, "w": w, "h": h})
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                debug_image,
                f"R{i + 1}",
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

    return debug_image, detected_regions


def collect_user_values_for_regions(enriched_regions):
    for region in enriched_regions:
        index = region["index"]
        label = region.get("label", "")

        user_value = input(
            f"Region {index} ({label}) - Enter value (skip to leave empty): "
        ).strip()

        if user_value:
            region["value"] = user_value
        else:
            region["value"] = ""

    return enriched_regions


def execute_ml_steps_generation(input_file, output_folder):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return None

    image = cv2.imread(input_file)
    if image is None:
        print(f"Error: Could not read image from '{input_file}'")
        return None

    debug_image, detected_regions = detect_masked_regions(image)
    print(f"Detected {len(detected_regions)} regions")

    enriched_regions = []
    for i, region in enumerate(detected_regions):
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        label = identify_region_type_from_left(image, x, y, w, h, output_folder, i + 1)
        enriched_regions.append(
            {
                "index": i + 1,
                "coordinates": {"x": x, "y": y, "width": w, "height": h},
                "label": label,
            }
        )

    enriched_regions = collect_user_values_for_regions(enriched_regions)

    os.makedirs(output_folder, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_file))[0]

    output_path = os.path.join(output_folder, f"{base_name}_detection.jpg")
    cv2.imwrite(output_path, debug_image)

    json_path = os.path.join(output_folder, f"{base_name}_analysis.json")
    result_json = {
        "input_file": input_file,
        "image_dimensions": {"width": image.shape[1], "height": image.shape[0]},
        "total_regions": len(enriched_regions),
        "regions": enriched_regions,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_json, f, indent=2, ensure_ascii=False)

    gemini_output_path = os.path.join(output_folder, f"{base_name}_final_generated.jpg")
    gemini_result = generate_payment_receipt_with_json_instructions(
        output_path, result_json, gemini_output_path
    )
    print(f"Gemini generation result: {gemini_result}")

    return {
        "input_file": input_file,
        "detected_regions": detected_regions,
        "enriched_regions": enriched_regions,
        "debug_image_path": output_path,
        "json_path": json_path,
        "gemini_output_path": gemini_result.get("output_path")
        if gemini_result.get("success")
        else None,
        "gemini_result": gemini_result,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect masked regions in payment receipt images"
    )
    parser.add_argument("-i", "--input", required=True, help="Input image file path")
    parser.add_argument("-o", "--output", default="output")
    args = parser.parse_args()
    result = execute_ml_steps_generation(args.input, args.output)
