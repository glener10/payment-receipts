# python src/usecases/ml_steps_generation.py -i 'dataset_just_banks_and_random_name/nu/0ercxg1eypyb_1766015257435.jpeg' -o 'output'
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

import cv2
import json

import pytesseract


def identify_region_type_from_left(
    image, x, y, w, h, debug_folder=None, region_index=0
):
    left_width = min(x, 350)

    if left_width < 10:
        return ""

    x_start = 0
    x_end = x - 5
    y_start = y
    y_end = y + h

    if x_end <= x_start or y_end <= y_start:
        return ""

    left_roi = image[y_start:y_end, x_start:x_end]

    if left_roi.size == 0:
        return ""

    if debug_folder:
        debug_roi_path = os.path.join(debug_folder, f"roi_left_{region_index}.jpg")
        cv2.imwrite(debug_roi_path, left_roi)
        print(f"  ROI saved: {debug_roi_path}")

    extracted_text = ""

    try:
        gray = cv2.cvtColor(left_roi, cv2.COLOR_BGR2GRAY)

        resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

        texts = []

        _, thresh1 = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        t1 = pytesseract.image_to_string(thresh1, config="--psm 6", lang="por").strip()
        texts.append(("OTSU+PSM6", t1))
        print(f"    Method 1 (OTSU+PSM6): '{t1}'")

        t2 = pytesseract.image_to_string(thresh1, config="--psm 7", lang="por").strip()
        texts.append(("OTSU+PSM7", t2))
        print(f"    Method 2 (OTSU+PSM7): '{t2}'")

        t3 = pytesseract.image_to_string(thresh1, config="--psm 11", lang="por").strip()
        texts.append(("OTSU+PSM11", t3))
        print(f"    Method 3 (OTSU+PSM11): '{t3}'")

        thresh2 = cv2.adaptiveThreshold(
            resized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        t4 = pytesseract.image_to_string(thresh2, config="--psm 6", lang="por").strip()
        texts.append(("ADAPTIVE+PSM6", t4))
        print(f"    Method 4 (ADAPTIVE+PSM6): '{t4}'")

        _, thresh3 = cv2.threshold(resized, 127, 255, cv2.THRESH_BINARY)
        t5 = pytesseract.image_to_string(thresh3, config="--psm 6", lang="por").strip()
        texts.append(("FIXED+PSM6", t5))
        print(f"    Method 5 (FIXED+PSM6): '{t5}'")

        inverted = cv2.bitwise_not(resized)
        t6 = pytesseract.image_to_string(inverted, config="--psm 6", lang="por").strip()
        texts.append(("INVERTED+PSM6", t6))
        print(f"    Method 6 (INVERTED+PSM6): '{t6}'")

        if debug_folder:
            os.makedirs(debug_folder, exist_ok=True)
            cv2.imwrite(
                os.path.join(debug_folder, f"roi_{region_index}_1_otsu.jpg"),
                thresh1,
            )
            cv2.imwrite(
                os.path.join(debug_folder, f"roi_{region_index}_2_adaptive.jpg"),
                thresh2,
            )
            cv2.imwrite(
                os.path.join(debug_folder, f"roi_{region_index}_3_fixed.jpg"),
                thresh3,
            )
            cv2.imwrite(
                os.path.join(debug_folder, f"roi_{region_index}_4_inverted.jpg"),
                inverted,
            )
            cv2.imwrite(
                os.path.join(debug_folder, f"roi_{region_index}_5_resized.jpg"),
                resized,
            )

        non_empty_texts = [(method, t) for method, t in texts if t and len(t) <= 50]

        if non_empty_texts:
            from collections import Counter

            text_list = [t for _, t in non_empty_texts]

            if len(text_list) >= 3:
                most_common = Counter(text_list).most_common(1)[0]
                if most_common[1] >= 2:
                    extracted_text = most_common[0]
                    print(
                        f"  Selected by frequency: '{extracted_text}' ({most_common[1]} votes)"
                    )
                else:
                    best_method, extracted_text = min(
                        non_empty_texts, key=lambda x: len(x[1])
                    )
                    print(
                        f"  Selected shortest: '{extracted_text}' (from {best_method})"
                    )
            else:
                best_method, extracted_text = min(
                    non_empty_texts, key=lambda x: len(x[1])
                )
                print(f"  Selected: '{extracted_text}' (from {best_method})")
        else:
            extracted_text = ""
            print(f"  No text extracted from any method")

        if debug_folder:
            os.makedirs(debug_folder, exist_ok=True)
            debug_text_path = os.path.join(
                debug_folder, f"roi_left_{region_index}_text.txt"
            )
            with open(debug_text_path, "w", encoding="utf-8") as f:
                f.write(f"Selected: {extracted_text}\n\n")
                for method, t in texts:
                    f.write(f"{method}:\n{t}\n\n")

    except Exception as e:
        print(f"  OCR error: {e}")
        import traceback

        traceback.print_exc()
        return ""

    return extracted_text.strip()


def detect_masked_regions(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY_INV)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detected_regions = []
    debug_image = image.copy()

    print("--- Starting Detection ---")
    print(f"Total contours found: {len(contours)}")

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        if w > 30 and h > 15:
            print(f"Masked region detected at: x={x}, y={y}, w={w}, h={h}")

            detected_regions.append({"x": x, "y": y, "w": w, "h": h})

            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)

            cv2.putText(
                debug_image,
                f"R{len(detected_regions)}",
                (x, y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )
        else:
            print(f"  Skipped small region: x={x}, y={y}, w={w}, h={h}")

    print(f"\nTotal masked regions detected: {len(detected_regions)}")
    return debug_image, detected_regions


def collect_user_values_for_regions(enriched_regions):
    print("\n=== Interactive Value Collection ===")
    print("For each detected region, enter the actual value.\n")

    for region in enriched_regions:
        index = region["index"]
        coords = region["coordinates"]
        label = region["label"]

        x, y, w, h = coords["x"], coords["y"], coords["width"], coords["height"]

        print(f"\nRegion {index}:")
        print(f"  Position: x={x}, y={y}, width={w}, height={h}")
        print(f"  Detected label: '{label}'")

        user_value = input(f"  Enter value (or press Enter to skip): ").strip()

        if user_value:
            region["value"] = user_value
            print(f"  ✓ Value set: '{user_value}'")
        else:
            region["value"] = ""
            print(f"  ⊘ Skipped")

    return enriched_regions


def execute_ml_steps_generation(input_file, output_folder=None):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        return None

    image = cv2.imread(input_file)
    if image is None:
        print(f"Error: Could not read image from '{input_file}'")
        return None

    print(f"Processing image: {input_file}")
    print(f"Image shape: {image.shape}")

    debug_image, detected_regions = detect_masked_regions(image)

    print(f"\nTotal regions detected: {len(detected_regions)}")

    print("\n--- Identifying Region Types ---")
    enriched_regions = []
    for i, region in enumerate(detected_regions):
        x, y, w, h = region["x"], region["y"], region["w"], region["h"]
        print(f"\nRegion {i + 1} at (x={x}, y={y}, w={w}, h={h}):")

        label = identify_region_type_from_left(image, x, y, w, h, output_folder, i + 1)

        enriched_region = {
            "index": i + 1,
            "coordinates": {"x": x, "y": y, "width": w, "height": h},
            "label": label,
        }
        enriched_regions.append(enriched_region)
        print(f"  Label: '{label}'")

    enriched_regions = collect_user_values_for_regions(enriched_regions)

    output_path = None
    json_path = None

    if output_folder:
        os.makedirs(output_folder, exist_ok=True)

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_path = os.path.join(output_folder, f"{base_name}_detection.jpg")
        cv2.imwrite(output_path, debug_image)
        print(f"\nDebug image saved: {output_path}")

        json_path = os.path.join(output_folder, f"{base_name}_analysis.json")
        result_json = {
            "input_file": input_file,
            "image_dimensions": {"width": image.shape[1], "height": image.shape[0]},
            "total_regions": len(enriched_regions),
            "regions": enriched_regions,
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)

        print(f"Analysis JSON saved: {json_path}")

    return {
        "input_file": input_file,
        "detected_regions": detected_regions,
        "enriched_regions": enriched_regions,
        "debug_image_path": output_path,
        "json_path": json_path,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect masked regions in payment receipt images"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input image file path",
    )
    parser.add_argument(
        "-o",
        "--output",
    )
    args = parser.parse_args()

    result = execute_ml_steps_generation(args.input, args.output)
