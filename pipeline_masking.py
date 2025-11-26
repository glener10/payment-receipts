import datetime
import subprocess
import argparse
import os

from src.utils.dirs import remove_empty_dirs


def remove_processed_files(input_dir, output_dir):
    """
    Remove files from input directory that successfully reached output directory

    Args:
        input_dir: Source directory to remove files from
        output_dir: Directory with successfully processed files
    """
    for root, _, files in os.walk(output_dir):
        for file in files:
            output_file_path = os.path.join(root, file)
            rel_path = os.path.relpath(output_file_path, output_dir)
            input_file_path = os.path.join(input_dir, rel_path)

            if os.path.exists(input_file_path):
                os.remove(input_file_path)


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

    remove_processed_files(args.input, args.output)
    remove_empty_dirs(args.input)
    remove_empty_dirs(temp_masked_dir)


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"pipeline_2: 🚀 starting process at {start_time}")

    main()

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    print(f"pipeline_2: ✅  execution finished. Total time: {total_time}")
