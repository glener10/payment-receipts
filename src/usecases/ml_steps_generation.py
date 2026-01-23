# python src/usecases/ml_steps_generation.py -i 'dataset_just_banks_and_random_name/nu/0ercxg1eypyb_1766015257435.jpeg' -o 'output_folder'
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

import cv2


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

    return {
        "input_file": input_file,
        "detected_regions": detected_regions,
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
        help="Output folder to save detection results",
    )
    args = parser.parse_args()

    result = execute_ml_steps_generation(args.input, args.output)
