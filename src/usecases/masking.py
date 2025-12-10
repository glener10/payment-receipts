# python src/usecases/masking.py -i 1.jpeg -o output.jpeg -c src/config/coordinates/nu/coordinates_output_1.json
import json
import os
import cv2
import fitz
from PIL import Image, ImageDraw


def mask_image(input_path, coordinates, output_path):
    try:
        input_image = cv2.imread(input_path)
        if input_image is None:
            raise ValueError(f"Could not load image: {input_path}")

        img = Image.open(input_path)
        draw = ImageDraw.Draw(img)

        for coord in coordinates:
            x = coord["x"]
            y = coord["y"]
            width = coord["width"]
            height = coord["height"]
            draw.rectangle([x, y, x + width, y + height], fill="black")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path)
        return True

    except Exception as e:
        print(f"error masking image: {e}")
        return False


def mask_pdf(input_path, coordinates, output_path):
    try:
        doc = fitz.open(input_path)
        page = doc[0]

        page_rect = page.rect
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        scale_x = page_rect.width / pix.width
        scale_y = page_rect.height / pix.height

        for coord in coordinates:
            pdf_x = coord["x"] * scale_x
            pdf_y = coord["y"] * scale_y
            pdf_width = coord["width"] * scale_x
            pdf_height = coord["height"] * scale_y

            rect = fitz.Rect(pdf_x, pdf_y, pdf_x + pdf_width, pdf_y + pdf_height)
            page.draw_rect(rect, color=(0, 0, 0), fill=(0, 0, 0))

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc.save(output_path)
        doc.close()
        return True

    except Exception as e:
        print(f"error masking PDF: {e}")
        return False


def mask_file(input_path, coordinates, output_path):
    _, ext = os.path.splitext(input_path)
    ext_lower = ext.lower()

    if ext_lower in [".jpg", ".jpeg", ".png"]:
        return mask_image(input_path, coordinates, output_path)
    elif ext_lower == ".pdf":
        return mask_pdf(input_path, coordinates, output_path)
    else:
        print(f"Unsupported file type: {ext}")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Input file path")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument(
        "-c", "--coordinates", required=True, help="Coordinates JSON file"
    )
    args = parser.parse_args()

    input_path = os.path.realpath(args.input)
    output_path = os.path.abspath(args.output)
    coordinates_path = os.path.realpath(args.coordinates)

    with open(coordinates_path, "r", encoding="utf-8") as f:
        coordinates = json.load(f)

    success = mask_file(input_path, coordinates, output_path)

    if success:
        print(f"masked file saved to: {output_path}")
    else:
        print(f"failed to mask file: {input_path}")
