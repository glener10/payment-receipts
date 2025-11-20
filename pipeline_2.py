import datetime
import subprocess
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline: mask sensitive data in payment receipts"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input directory containing files to mask (person/bank/files structure)",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory for masked files",
    )

    args = parser.parse_args()

    print(
        f"pipeline_2: executing sensitive_data_masker.py to mask files from {args.input} into {args.output}"
    )
    subprocess.run(
        f"python sensitive_data_masker.py -i '{args.input}' -o '{args.output}'",
        shell=True,
        check=True,
    )


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"pipeline_2: 🚀 starting process at {start_time}")

    main()

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    print(f"pipeline_2: ✅  execution finished. Total time: {total_time}")
