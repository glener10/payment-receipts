import argparse


def get_args():
    parser = argparse.ArgumentParser(
        description="llm-liaa-payment-receipt-sensitive-data-masker"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="input path to the payments receipts to mask sensitive data",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        default="classify_output",
        help="output path",
    )
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="use local model via Ollama instead of Gemini (better privacy)",
    )
    args = parser.parse_args()
    return args
