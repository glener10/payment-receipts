# python src/usecases/guardrails.py -i '1.jpeg'
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

from src.clients.gemini import check_sensitive_data_with_gemini
from src.clients.ollama import check_sensitive_data_with_ollama


def execute_guardrails(input_path, use_ollama=False):
    check_function = (
        check_sensitive_data_with_ollama
        if use_ollama
        else check_sensitive_data_with_gemini
    )
    input_path = os.path.realpath(input_path)

    result = check_function(input_path)

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input file",
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="use local model via Ollama instead of Gemini (better privacy)",
    )
    args = parser.parse_args()

    response = execute_guardrails(args.input, args.ollama)

    if response.get("has_sensitive_data", True):
        analysis = response.get("analysis", "No details provided")
        print(f"sensitive data found - {analysis}")
    else:
        print(f"all data masked - {response['analysis']}")
