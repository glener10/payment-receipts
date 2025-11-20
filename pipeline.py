import subprocess
import argparse
import os


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline: organize files by name, then classify by bank"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Input directory containing files to organize",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output directory for organized and classified files",
    )

    args = parser.parse_args()

    temp_organized = "z_temp_organized"

    subprocess.run(
        f"python file_organizer.py -i '{args.input}' -o '{temp_organized}'",
        shell=True,
        check=True,
    )

    for person_folder in os.listdir(temp_organized):
        person_path = os.path.join(temp_organized, person_folder)
        if os.path.isdir(person_path):
            output_person_path = os.path.join(args.output, person_folder)
            subprocess.run(
                f"python receipt_organizer.py -i '{person_path}' -o '{output_person_path}'",
                shell=True,
                check=True,
            )


if __name__ == "__main__":
    main()
