import asyncio
import datetime
import os

from src.modules.sensitive_data_masker.execute import (
    process_files_with_coordinate_matching,
)
from src.modules.sensitive_data_masker.args import get_args


async def main():
    args = get_args()
    real_path = os.path.realpath(args.input)
    output_dir = os.path.abspath(args.output)

    await process_files_with_coordinate_matching(real_path, output_dir)


if __name__ == "__main__":
    start_time = datetime.datetime.now()
    print(f"sensitive_data_masker: 🚀 starting process at {start_time}")

    asyncio.run(main())

    end_time = datetime.datetime.now()
    total_time = end_time - start_time
    print(f"sensitive_data_masker: ✅ execution finished. Total time: {total_time}")
