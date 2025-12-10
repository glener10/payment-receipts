import os
import argparse
import random
from collections import defaultdict


def count_files_by_user(root_path, blacklist=None):
    if blacklist is None:
        blacklist = []

    blacklist_lower = [name.lower() for name in blacklist]
    user_files = defaultdict(int)

    real_path = os.path.realpath(root_path)

    if not os.path.exists(real_path):
        print(f"❌ error: The path '{real_path}' does not exist.")
        return None

    if not os.path.isdir(real_path):
        print(f"❌ error: The path '{real_path}' is not a directory.")
        return None

    for root, dirs, files in os.walk(real_path, followlinks=True):
        rel_path = os.path.relpath(root, real_path)

        if rel_path == ".":
            continue

        path_parts = rel_path.split(os.sep)

        if len(path_parts) >= 2:
            user = path_parts[0]

            if user.lower() in blacklist_lower:
                continue

            file_count = len(
                [f for f in files if os.path.isfile(os.path.join(root, f))]
            )
            user_files[user] += file_count

    return dict(user_files)


def perform_sortition(user_files):
    if not user_files:
        print("❌ No users to sortition")
        return None

    weighted_pool = []
    for user, count in user_files.items():
        weighted_pool.extend([user] * count)

    random.shuffle(weighted_pool)

    selected_index = random.randint(0, len(weighted_pool) - 1)
    return weighted_pool[selected_index]


def main():
    parser = argparse.ArgumentParser(description="Weighted sortition for users")
    parser.add_argument(
        "-i", "--input", required=True, help="Input path to root folder"
    )
    args = parser.parse_args()

    root_path = os.path.abspath(args.input)
    user_files = count_files_by_user(root_path, blacklist=["Glener"])
    if not user_files:
        print("❌ No files found")
        return

    print("📊 participants:\n")
    for user in sorted(user_files.keys()):
        count = user_files[user]
        print(f"{user} {count} itens")

    winner = perform_sortition(user_files)

    if winner:
        print(f"\n🎲 Sortition winner:\n\n{winner}")


if __name__ == "__main__":
    main()
