import os
from PIL import Image, ImageDraw
import fitz


def apply_mask_to_image(image_path, coordinates, output_path):
    try:
        img = Image.open(image_path)
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
        print(f"❌ Error masking image {image_path}: {e}")
        return False


def apply_mask_to_pdf(pdf_path, coordinates, output_path):
    try:
        doc = fitz.open(pdf_path)
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
        print(f"❌ Error masking PDF {pdf_path}: {e}")
        return False
