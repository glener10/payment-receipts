# python src/usecases/ml_steps_generation.py -i 'dataset_just_banks_and_random_name/nu/0ercxg1eypyb_1766015257435.jpeg' -o 'output'
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

import cv2
import json
import numpy as np

import pytesseract


def detect_text_characteristics_from_region(
    region_roi, region_index=0, debug_folder=None
):
    """
    Detect comprehensive text characteristics from a masked region.
    Analyzes font properties, color, alignment, and style.

    Returns a dict with detailed text characteristics.
    """
    if region_roi is None or region_roi.size == 0:
        return {"detected": False, "characteristics": {}}

    try:
        # Convert to grayscale
        if len(region_roi.shape) == 3:
            gray = cv2.cvtColor(region_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_roi

        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # Detect edges to analyze stroke characteristics
        edges = cv2.Canny(gray, 100, 200)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Analyze stroke width
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        eroded = cv2.erode(thresh, kernel, iterations=1)
        white_pixels_original = cv2.countNonZero(thresh)
        white_pixels_eroded = cv2.countNonZero(eroded)

        stroke_width = "normal"
        if white_pixels_eroded < white_pixels_original * 0.3:
            stroke_width = "bold"
        elif white_pixels_eroded > white_pixels_original * 0.7:
            stroke_width = "light"

        # Detect serif characteristics
        serif_indicators = 0
        if len(contours) > 0:
            small_contours = [
                cnt
                for cnt in contours
                if cv2.contourArea(cnt) < 50 and cv2.contourArea(cnt) > 5
            ]
            serif_indicators = len(small_contours)

        has_serifs = (
            serif_indicators > len(contours) * 0.1 if len(contours) > 0 else False
        )
        font_style = "serif" if has_serifs else "sans-serif"

        # Detect text color from non-masked pixels
        hsv = cv2.cvtColor(region_roi, cv2.COLOR_BGR2HSV)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 50, 255])
        mask_inv = cv2.bitwise_not(cv2.inRange(hsv, lower_white, upper_white))

        h_values = hsv[mask_inv > 0, 0]
        s_values = hsv[mask_inv > 0, 1]
        v_values = hsv[mask_inv > 0, 2]

        text_color = "unknown"
        hex_color = "#000000"

        if len(h_values) > 0:
            avg_h = int(np.mean(h_values))
            avg_s = int(np.mean(s_values))
            avg_v = int(np.mean(v_values))

            # Convert HSV to RGB for hex
            hsv_array = np.uint8([[[avg_h, avg_s, avg_v]]])
            rgb_array = cv2.cvtColor(hsv_array, cv2.COLOR_HSV2RGB)
            r, g, b = rgb_array[0][0]
            hex_color = "#{:02X}{:02X}{:02X}".format(int(r), int(g), int(b))

            # Classify color
            if avg_s < 50:
                text_color = "black" if avg_v < 100 else "gray"
            else:
                text_color = "colored"

        # Detect horizontal alignment by analyzing text distribution
        moments = cv2.moments(thresh)
        if moments["m00"] != 0:
            cx = int(moments["m10"] / moments["m00"])
            region_center_x = region_roi.shape[1] // 2

            if abs(cx - region_center_x) < region_roi.shape[1] * 0.1:
                alignment = "center"
            elif cx < region_roi.shape[1] * 0.3:
                alignment = "left"
            else:
                alignment = "right"
        else:
            alignment = "unknown"

        characteristics = {
            "font_style": font_style,
            "stroke_width": stroke_width,
            "has_serifs": has_serifs,
            "text_color": text_color,
            "hex_color": hex_color,
            "alignment": alignment,
            "confidence": 70,
        }

        if debug_folder:
            os.makedirs(debug_folder, exist_ok=True)
            cv2.imwrite(
                os.path.join(debug_folder, f"text_analysis_{region_index}_edges.jpg"),
                edges,
            )

        return {"detected": True, "characteristics": characteristics}

    except Exception as e:
        print(f"  Text analysis error: {e}")
        return {"detected": False, "characteristics": {}, "error": str(e)}


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


def inpaint_regions_from_json(image, json_data, output_folder=None):
    """
    Inpaint masked regions using data from JSON analysis file.
    Replaces black masks with background color and renders the extracted text values.

    Args:
        image: Input image (with black masks)
        json_data: Dictionary with regions data from analysis
        output_folder: Optional folder to save debug images

    Returns:
        Restored image with masks replaced and text rendered
    """
    print("\n--- Inpainting Masked Regions and Rendering Values ---")

    restored_image = image.copy()

    regions = json_data.get("regions", [])
    print(f"Processing {len(regions)} regions for inpainting...")

    for region in regions:
        coords = region["coordinates"]
        x = coords["x"]
        y = coords["y"]
        w = coords["width"]
        h = coords["height"]
        region_idx = region["index"]
        value = region.get("value", "")

        print(f"\nRegion {region_idx} at (x={x}, y={y}, w={w}, h={h}): Processing...")
        print(f"  - Value to render: '{value}'")

        try:
            # Get the dominant background color around the region
            border_size = 15
            bg_colors = []

            # Sample colors from borders around the region
            # Top border
            if y > border_size:
                top_roi = image[max(0, y - border_size) : y, x : x + w]
                if top_roi.size > 0:
                    bg_colors.append(cv2.mean(top_roi)[:3])

            # Bottom border
            if y + h < image.shape[0] - border_size:
                bottom_roi = image[
                    y + h : min(image.shape[0], y + h + border_size), x : x + w
                ]
                if bottom_roi.size > 0:
                    bg_colors.append(cv2.mean(bottom_roi)[:3])

            # Left border
            if x > border_size:
                left_roi = image[y : y + h, max(0, x - border_size) : x]
                if left_roi.size > 0:
                    bg_colors.append(cv2.mean(left_roi)[:3])

            # Right border
            if x + w < image.shape[1] - border_size:
                right_roi = image[
                    y : y + h, x + w : min(image.shape[1], x + w + border_size)
                ]
                if right_roi.size > 0:
                    bg_colors.append(cv2.mean(right_roi)[:3])

            # Calculate average background color
            if bg_colors:
                avg_bg_color = tuple(
                    int(np.mean([c[i] for c in bg_colors])) for i in range(3)
                )
                print(f"  - Detected background color (BGR): {avg_bg_color}")

                # Fill the region with the average background color
                restored_image[y : y + h, x : x + w] = avg_bg_color

                # Apply bilateral filter to smooth the region and blend edges
                region_roi = restored_image[y : y + h, x : x + w]
                smoothed = cv2.bilateralFilter(region_roi, 9, 75, 75)
                restored_image[y : y + h, x : x + w] = smoothed

                # Apply morphological closing to fill small holes
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                morphed = cv2.morphologyEx(smoothed, cv2.MORPH_CLOSE, kernel)
                restored_image[y : y + h, x : x + w] = morphed

                print(f"  ✓ Background filled")

                # If value exists, render it on the region
                if value and len(value) > 0:
                    # Get text characteristics if available
                    text_analysis = region.get("text_analysis", {})
                    text_chars = text_analysis.get("characteristics", {})

                    # Determine text color
                    text_color = (0, 0, 0)  # Default to black
                    if text_chars.get("hex_color"):
                        hex_color = text_chars["hex_color"].lstrip("#")
                        r = int(hex_color[0:2], 16)
                        g = int(hex_color[2:4], 16)
                        b = int(hex_color[4:6], 16)
                        text_color = (b, g, r)  # Convert to BGR for OpenCV

                    # Determine font based on detected characteristics
                    font = (
                        cv2.FONT_HERSHEY_DUPLEX
                        if text_chars.get("font_style") == "serif"
                        else cv2.FONT_HERSHEY_SIMPLEX
                    )

                    # Determine thickness based on stroke width
                    stroke_width = text_chars.get("stroke_width", "normal")
                    if stroke_width == "bold":
                        font_thickness = max(2, int(h / 30))
                    elif stroke_width == "light":
                        font_thickness = max(1, int(h / 50))
                    else:
                        font_thickness = max(1, int(h / 40))

                    # Calculate font size based on region height
                    font_scale = max(0.3, min(1.0, h / 30.0))

                    # Get text size
                    text_size = cv2.getTextSize(
                        value, font, font_scale, font_thickness
                    )[0]

                    # Calculate position based on detected alignment
                    alignment = text_chars.get("alignment", "left")
                    if alignment == "center":
                        text_x = x + max(2, (w - text_size[0]) // 2)
                    elif alignment == "right":
                        text_x = x + max(2, w - text_size[0] - 2)
                    else:  # left
                        text_x = x + 2

                    text_y = y + max(text_size[1] + 2, (h + text_size[1]) // 2)

                    # Put text on the image
                    cv2.putText(
                        restored_image,
                        value,
                        (text_x, text_y),
                        font,
                        font_scale,
                        text_color,
                        font_thickness,
                    )

                    print(f"  ✓ Text rendered: '{value}'")
                    print(f"    - Font: {text_chars.get('font_style', 'unknown')}")
                    print(
                        f"    - Color: {text_chars.get('text_color', 'unknown')} {text_chars.get('hex_color', '')}"
                    )
                    print(f"    - Alignment: {alignment}")
                    print(f"    - Thickness: {font_thickness}")
                else:
                    print(f"  - No value to render")

                if output_folder:
                    os.makedirs(output_folder, exist_ok=True)

                    # Save intermediate results for debugging
                    cv2.imwrite(
                        os.path.join(output_folder, f"inpaint_{region_idx}_filled.jpg"),
                        restored_image,
                    )
            else:
                # Fallback: just fill with white if no background detected
                restored_image[y : y + h, x : x + w] = (255, 255, 255)
                print(
                    f"  ⚠ Region {region_idx}: No background detected, filled with white"
                )

        except Exception as e:
            print(f"  ⚠ Error processing region {region_idx}: {e}")
            import traceback

            traceback.print_exc()

    return restored_image


def collect_user_values_for_regions(image, enriched_regions, output_folder=None):
    print("\n=== Interactive Value Collection and Text Analysis ===")
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

            # Analyze text characteristics from the region
            value_roi = image[y : y + h, x : x + w]
            text_chars = detect_text_characteristics_from_region(
                value_roi, index, output_folder
            )
            region["text_analysis"] = text_chars

            if text_chars["detected"]:
                chars = text_chars["characteristics"]
                print(f"  ✓ Text characteristics detected:")
                print(f"    - Font: {chars.get('font_style', 'unknown')}")
                print(f"    - Stroke: {chars.get('stroke_width', 'unknown')}")
                print(
                    f"    - Color: {chars.get('text_color', 'unknown')} ({chars.get('hex_color', '#000000')})"
                )
                print(f"    - Alignment: {chars.get('alignment', 'unknown')}")
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

    enriched_regions = collect_user_values_for_regions(
        image, enriched_regions, output_folder
    )

    output_path = None
    json_path = None
    restored_image_path = None

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

        # Inpaint regions using the JSON data
        restored_image = inpaint_regions_from_json(image, result_json, output_folder)

        # Save restored image
        restored_image_path = os.path.join(output_folder, f"{base_name}_restored.jpg")
        cv2.imwrite(restored_image_path, restored_image)
        print(f"Restored image saved: {restored_image_path}")

    return {
        "input_file": input_file,
        "detected_regions": detected_regions,
        "enriched_regions": enriched_regions,
        "debug_image_path": output_path,
        "restored_image_path": restored_image_path,
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
