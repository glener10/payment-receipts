import tempfile
import fitz
import cv2
import numpy as np


def pdf_to_image(pdf_path):
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

    img_data = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )

    if pix.n == 4:
        img = cv2.cvtColor(img_data, cv2.COLOR_RGBA2BGR)
    else:
        img = cv2.cvtColor(img_data, cv2.COLOR_RGB2BGR)

    doc.close()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    cv2.imwrite(temp_file.name, img)
    temp_file.close()

    return temp_file.name
