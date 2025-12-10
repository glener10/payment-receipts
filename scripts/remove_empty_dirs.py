import os
import argparse


def remove_empty_dirs(root_dir):
    for dirpath, dirnames, _ in os.walk(root_dir, topdown=False):
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            if not os.listdir(full_path):
                os.rmdir(full_path)


def main():
    parser = argparse.ArgumentParser(description="Remove empty directories recursively")
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="Root directory to clean empty folders from",
    )
    args = parser.parse_args()

    root_dir = os.path.abspath(args.input)
    if not os.path.exists(root_dir):
        return

    remove_empty_dirs(root_dir)


if __name__ == "__main__":
    main()
