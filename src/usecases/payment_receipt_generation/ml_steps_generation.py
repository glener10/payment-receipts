# python src/usecases/payment_receipt_generation/ml_steps_generation.py -i 'dataset_just_banks_and_random_name/nu/0ercxg1eypyb_1766015257435.jpeg'
import os
import sys
import cv2
import json
import numpy as np
import pytesseract

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    )


def detect_text_characteristics_from_region(region_roi, debug_folder, region_index=0):
    if region_roi is None or region_roi.size == 0:
        return {"detected": False, "characteristics": {}}

    try:
        if len(region_roi.shape) == 3:
            gray = cv2.cvtColor(region_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = region_roi

        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        edges = cv2.Canny(gray, 100, 200)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        eroded = cv2.erode(thresh, kernel, iterations=1)
        white_pixels_original = cv2.countNonZero(thresh)
        white_pixels_eroded = cv2.countNonZero(eroded)

        stroke_width = "normal"
        if white_pixels_eroded < white_pixels_original * 0.3:
            stroke_width = "bold"
        elif white_pixels_eroded > white_pixels_original * 0.7:
            stroke_width = "light"

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

            hsv_array = np.uint8([[[avg_h, avg_s, avg_v]]])
            rgb_array = cv2.cvtColor(hsv_array, cv2.COLOR_HSV2RGB)
            r, g, b = rgb_array[0][0]
            hex_color = "#{:02X}{:02X}{:02X}".format(int(r), int(g), int(b))

            if avg_s < 50:
                text_color = "black" if avg_v < 100 else "gray"
            else:
                text_color = "colored"

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

        os.makedirs(debug_folder, exist_ok=True)
        cv2.imwrite(
            os.path.join(debug_folder, f"text_analysis_{region_index}_edges.jpg"),
            edges,
        )

        return {"detected": True, "characteristics": characteristics}

    except Exception as e:
        print(f"  Text analysis error: {e}")
        return {"detected": False, "characteristics": {}, "error": str(e)}


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


def inpaint_regions_from_json(image, json_data, output_folder=None):
    restored_image = image.copy()
    regions = json_data.get("regions", [])

    for region in regions:
        coords = region["coordinates"]
        x, y, w, h = coords["x"], coords["y"], coords["width"], coords["height"]
        value = region.get("value", "")

        try:
            border_size = 15
            bg_colors = []

            if y > border_size:
                top_roi = image[max(0, y - border_size) : y, x : x + w]
                if top_roi.size > 0:
                    bg_colors.append(cv2.mean(top_roi)[:3])

            if y + h < image.shape[0] - border_size:
                bottom_roi = image[
                    y + h : min(image.shape[0], y + h + border_size), x : x + w
                ]
                if bottom_roi.size > 0:
                    bg_colors.append(cv2.mean(bottom_roi)[:3])

            if x > border_size:
                left_roi = image[y : y + h, max(0, x - border_size) : x]
                if left_roi.size > 0:
                    bg_colors.append(cv2.mean(left_roi)[:3])

            if x + w < image.shape[1] - border_size:
                right_roi = image[
                    y : y + h, x + w : min(image.shape[1], x + w + border_size)
                ]
                if right_roi.size > 0:
                    bg_colors.append(cv2.mean(right_roi)[:3])

            if bg_colors:
                avg_bg = tuple(
                    int(np.mean([c[i] for c in bg_colors])) for i in range(3)
                )
                restored_image[y : y + h, x : x + w] = avg_bg
                restored_image[y : y + h, x : x + w] = cv2.bilateralFilter(
                    restored_image[y : y + h, x : x + w], 9, 75, 75
                )
                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
                restored_image[y : y + h, x : x + w] = cv2.morphologyEx(
                    restored_image[y : y + h, x : x + w], cv2.MORPH_CLOSE, kernel
                )

                if value:
                    text_chars = region.get("text_analysis", {}).get(
                        "characteristics", {}
                    )
                    hex_c = text_chars.get("hex_color", "#000000").lstrip("#")
                    text_color = (
                        int(hex_c[4:6], 16),
                        int(hex_c[2:4], 16),
                        int(hex_c[0:2], 16),
                    )
                    font = (
                        cv2.FONT_HERSHEY_DUPLEX
                        if text_chars.get("font_style") == "serif"
                        else cv2.FONT_HERSHEY_SIMPLEX
                    )

                    stroke = text_chars.get("stroke_width", "normal")
                    if stroke == "bold":
                        thick = max(2, int(h / 30))
                    elif stroke == "light":
                        thick = max(1, int(h / 50))
                    else:
                        thick = max(1, int(h / 40))

                    scale = max(0.3, min(1.0, h / 30.0))
                    text_size = cv2.getTextSize(value, font, scale, thick)[0]
                    align = text_chars.get("alignment", "left")

                    if align == "center":
                        text_x = x + max(2, (w - text_size[0]) // 2)
                    elif align == "right":
                        text_x = x + max(2, w - text_size[0] - 2)
                    else:
                        text_x = x + 2

                    text_y = y + max(text_size[1] + 2, (h + text_size[1]) // 2)
                    cv2.putText(
                        restored_image,
                        value,
                        (text_x, text_y),
                        font,
                        scale,
                        text_color,
                        thick,
                    )

            else:
                restored_image[y : y + h, x : x + w] = (255, 255, 255)

            if output_folder:
                os.makedirs(output_folder, exist_ok=True)
                cv2.imwrite(
                    os.path.join(
                        output_folder, f"inpaint_{region['index']}_filled.jpg"
                    ),
                    restored_image,
                )

        except Exception:
            pass

    return restored_image


def collect_user_values_for_regions(image, enriched_regions, output_folder=None):
    for region in enriched_regions:
        index = region["index"]
        label = region.get("label", "")
        coords = region["coordinates"]
        x, y, w, h = coords["x"], coords["y"], coords["width"], coords["height"]

        user_value = input(
            f"Region {index} ({label}) - Enter value (skip to leave empty): "
        ).strip()

        if user_value:
            region["value"] = user_value
            value_roi = image[y : y + h, x : x + w]
            text_chars = detect_text_characteristics_from_region(
                value_roi, output_folder, index
            )
            region["text_analysis"] = text_chars
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

    enriched_regions = collect_user_values_for_regions(
        image, enriched_regions, output_folder
    )

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

    restored_image = inpaint_regions_from_json(image, result_json, output_folder)
    restored_image_path = os.path.join(output_folder, f"{base_name}_restored.jpg")
    cv2.imwrite(restored_image_path, restored_image)

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
    parser.add_argument("-i", "--input", required=True, help="Input image file path")
    parser.add_argument("-o", "--output", default="output")
    args = parser.parse_args()
    result = execute_ml_steps_generation(args.input, args.output)
