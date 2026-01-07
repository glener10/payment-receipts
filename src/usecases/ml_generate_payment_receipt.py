# python src/usecases/ml_generate_fake_payment_receipt.py -i 'dataset_just_banks_and_random_name' -b 'nu' -e 'jpeg'
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )


def execute_ml_generate_fake_payment_receipt(input_folder, bank, extension):
    input_folder = os.path.realpath(input_folder)
    bank_folder = os.path.join(input_folder, bank)

    if not os.path.exists(bank_folder):
        print(f"Error: Bank folder '{bank_folder}' not found")
        return []

    if not os.path.isdir(bank_folder):
        print(f"Error: '{bank_folder}' is not a folder")
        return []

    if extension.startswith("."):
        extension = extension[1:]

    files = []
    for filename in os.listdir(bank_folder):
        if filename.endswith(f".{extension}"):
            file_path = os.path.join(bank_folder, filename)
            files.append(file_path)

    if not files:
        print(f"No files with extension '.{extension}' found in '{bank_folder}'")

    return files


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input folder containing the bank folders",
    )
    parser.add_argument(
        "-b",
        "--bank",
        required=True,
        help="Bank name (folder inside the input)",
    )
    parser.add_argument(
        "-e",
        "--extension",
        required=True,
        help="File extension (e.g., jpeg, pdf, png)",
    )
    args = parser.parse_args()

    files = execute_ml_generate_fake_payment_receipt(
        args.input, args.bank, args.extension
    )
