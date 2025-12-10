# file: python main.py -i 'example.jpeg' -n '99pay'
# directory: python main.py -i 'z'
# optional: -o 'output/' --ollama
import argparse
import os

from src.usecases.load_templates import load_bank_templates
from src.usecases.matcher import match_template
from src.usecases.masking import mask_file
from src.usecases.guardrails import execute_guardrails


def execute(input_path, bank_name, extension, output_path, use_ollama=False):
    templates = load_bank_templates(bank_name, extension)
    match = match_template(input_path, templates=templates, use_ollama=use_ollama)
    if not match:
        print("no matching template found")
        return None

    print(f"matched template: {match['name']}{match['file_extension']}")

    if not mask_file(input_path, match["coordinates"], output_path):
        print("error masking file")
        return None

    guardrails = execute_guardrails(output_path, use_ollama)
    if guardrails["has_sensitive_data"]:
        print("guardrails check failed")
        # os.remove(output_path)
        return None

    print("guardrails check passed")
    # os.remove(input_path)


def main():
    parser = argparse.ArgumentParser(description="Mask sensitive data")
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input file or directory. When using directory, use structure: /user/bank/files",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output",
        help="Output directory (default: output)",
    )
    parser.add_argument(
        "-n", "--name", required=False, help="bank name, use only your input is a file"
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="use local model via Ollama instead of Gemini (better privacy)",
    )
    args = parser.parse_args()

    input_path = os.path.realpath(args.input)

    if not os.path.exists(input_path):
        print(f"❌ Input path does not exist: {input_path}")
        return

    if os.path.isfile(input_path):
        output_path = os.path.realpath(f"{args.output}/{os.path.basename(input_path)}")
        execute(
            input_path,
            args.name,
            os.path.splitext(input_path)[1],
            output_path,
            args.ollama,
        )
    else:
        for root, _, files in os.walk(input_path):
            for file in files:
                _, ext = os.path.splitext(file)
                if ext.lower() not in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".pdf",
                ]:
                    print(f"skipping unsupported file type: {file}")
                    continue

                file_path = os.path.join(root, file)

                # Extract bank name from path structure: /user/bank/files
                rel_path = os.path.relpath(file_path, input_path)
                parts = rel_path.split(os.sep)

                if len(parts) < 2:
                    print(f"invalid path structure: {file_path}")
                    continue
                bank_name = parts[1]
                user_name = parts[0]

                output_path = f"{args.output}/{user_name}/{bank_name}/{file}"
                real_output_path = os.path.realpath(output_path)
                execute(file_path, bank_name, ext, real_output_path, args.ollama)


if __name__ == "__main__":
    main()
