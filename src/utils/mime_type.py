import os


def get_mime_type(input):
    if input.startswith("."):
        suffix = input.lower()
    else:
        _, suffix = os.path.splitext(input)
        suffix = suffix.lower()

    if suffix == ".png":
        return "image/png"
    elif suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"
    elif suffix == ".pdf":
        return "application/pdf"

    raise ValueError(f"Unsupported file type: {suffix}")
