# python src/usecases/generate_payment_receipt.py -i templates/anonimizados -e pdf -o output/generated_receipts
# https://github.com/Gnoario/deepfake-inspector/blob/main/model.py train with tensorflow or other
import argparse
import os
import sys
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

from src.clients.gemini import generate_payment_receipt_with_gemini


def collect_templates_by_extension(input_dir, extension):
    if not extension.startswith("."):
        extension = f".{extension}"

    templates = []

    input_path = Path(input_dir)
    if not input_path.exists():
        raise ValueError(f"directory not found: {input_dir}")

    for file_path in input_path.rglob(f"*{extension}"):
        if file_path.is_file():
            templates.append(str(file_path.absolute()))

    return templates


def generate_payment_receipt(input, extension, output, limit=None):
    templates = collect_templates_by_extension(input, extension)

    if not templates:
        print(f"no templates found with extension '{extension}' in directory: {input}")
        return

    if limit and limit > 0:
        templates = templates[:limit]

    result = generate_payment_receipt_with_gemini(templates, output)

    if result["success"]:
        print("✅ payment receipt generated successfully!")
    else:
        print(f"❌ error generating payment receipt: {result['error']}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Gera comprovantes de pagamento Pix usando Gemini treinado com templates anonimizados"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Diretório contendo os templates anonimizados",
    )
    parser.add_argument(
        "-e",
        "--extension",
        required=True,
        help="Extensão dos templates a serem utilizados (ex: pdf, png, jpg)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output/generated_receipt.png",
        help="Caminho do arquivo de saída (padrão: output/generated_receipt.png)",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=None,
        help="Limitar o número de templates a serem usados (opcional)",
    )

    args = parser.parse_args()

    generate_payment_receipt(args.input, args.extension, args.output, args.limit)


if __name__ == "__main__":
    main()
