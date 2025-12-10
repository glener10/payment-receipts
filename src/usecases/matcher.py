# python src/usecases/matcher.py -n 99pay -i 1.jpeg
import argparse
import os
import sys

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    )

from src.clients.ollama import compare_templates_with_ollama
from src.clients.gemini import compare_templates_with_gemini
from src.usecases.load_templates import load_bank_templates


def match_template(
    input_path,
    templates=None,
    use_ollama=False,
    bank_name=None,
    file_extension=None,
):
    if not templates:
        templates = load_bank_templates(bank_name, file_extension)

    if not templates:
        print(
            f"no templates found for bank '{bank_name}' with extension '{file_extension}'"
        )
        return None

    compare_function = (
        compare_templates_with_ollama if use_ollama else compare_templates_with_gemini
    )

    matchs_found = []
    for template in templates:
        result = compare_function(template["reference_path"], input_path)

        confidence = result.get("confidence", 0.0)
        is_match = result.get("is_match", False)

        if is_match:
            match = {
                "template": template,
                "confidence": confidence,
                "reason": result.get("reason", ""),
                "is_match": is_match,
            }
            matchs_found.append(match)

    if not matchs_found:
        return None

    # TODO: Create a tie-breaking method between N templates
    best_match = max(matchs_found, key=lambda x: x["confidence"])["template"]
    return best_match


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", required=True, help="Bank name")
    parser.add_argument("-i", "--input", required=True, help="Input file path")
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="use local model via Ollama instead of Gemini (better privacy)",
    )
    args = parser.parse_args()

    extension = os.path.splitext(args.input)[1]
    result = match_template(
        args.input,
        templates=None,
        use_ollama=args.ollama,
        bank_name=args.name,
        file_extension=extension,
    )

    if result:
        print(f"best match: {result['name']}{result['file_extension']}")
    else:
        print("no match found")
