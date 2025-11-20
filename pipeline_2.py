import datetime
import subprocess
import argparse

from src.utils.dirs import remove_empty_dirs


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline: mask sensitive data and validate with guardrails"
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
        help="Output directory for validated masked files",
    )

    args = parser.parse_args()

    temp_masked_dir = "z_temp_masked_files"

    print(
        f"pipeline_2: executing sensitive_data_masker.py to mask files from {args.input} into {temp_masked_dir}"
    )
    subprocess.run(
        f"python sensitive_data_masker.py -i '{args.input}' -o '{temp_masked_dir}'",
        shell=True,
        check=True,
    )

    print(
        f"pipeline_2: executing guardrails.py to validate masked files from {temp_masked_dir} into {args.output}"
    )
    subprocess.run(
        f"python guardrails.py -i '{temp_masked_dir}' -o '{args.output}'",
        shell=True,
        check=True,
    )

    remove_empty_dirs(temp_masked_dir)


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"pipeline_2: 🚀 starting process at {start_time}")

    main()

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    print(f"pipeline_2: ✅  execution finished. Total time: {total_time}")
