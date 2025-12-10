# python src/usecases/get_bank_of_payment_receipt.py -i example.jpeg
import argparse
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

from src.clients.gemini import get_bank_of_payment_receipt


def identify_bank(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    result = get_bank_of_payment_receipt(file_path)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Input file path")
    args = parser.parse_args()

    result = identify_bank(args.input)

    if result.get("classify"):
        print(f"Bank identified: {result['classify']}")
    else:
        print("Could not identify bank")


# def format_folder_name(name):
#     folder_name = "".join(
#         c for c in name if c.isalnum() or c in (" ", "-", "_")
#     ).strip()
#     folder_name = folder_name.replace(" ", "_")
#     folder_name = (
#         unicodedata.normalize("NFKD", folder_name)
#         .encode("ASCII", "ignore")
#         .decode("ASCII")
#     )
#     return folder_name.lower()


# def move_files_to_specified_bank_folders(results_from_models, output_path):
#     created_folders = set()

#     for result in results_from_models:
#         classify = result.get("classify")

#         folder_name = "unknown_classification"
#         if classify:
#             folder_name = format_folder_name(classify)

#         classification_folder_path = os.path.join(output_path, folder_name)

#         if folder_name not in created_folders:
#             os.makedirs(classification_folder_path, exist_ok=True)
#             created_folders.add(folder_name)

#         path_of_file_without_classification = result.get("path")
#         file_name_without_classification = os.path.basename(
#             path_of_file_without_classification
#         )
#         destination = os.path.join(
#             classification_folder_path, file_name_without_classification
#         )

#         shutil.move(path_of_file_without_classification, destination)
#         # shutil.copy(path_of_file_without_classification, destination)
